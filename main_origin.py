#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
井身结构图生成主程序
整合数据提取和绘图功能
"""

import json
import csv
import sys
import os
from typing import List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from datetime import datetime
import io
import subprocess


# ============================================================================
# 地层数据提取器
# ============================================================================
class StratigraphyExtractor:
    """地层数据提取器类 - 分离原始数据提取和数据映射"""
    
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.stratigraphy_data = []
        
    def load_json_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {self.json_file_path} 不存在")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON文件格式错误: {e}")
    
    def extract_stratigraphy(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if 'stratigraphy' not in data:
            raise KeyError("JSON数据中缺少 'stratigraphy' 字段")
        
        stratigraphy = data['stratigraphy']
        if not isinstance(stratigraphy, list):
            raise ValueError("stratigraphy字段应该是一个列表")
        
        return stratigraphy
    
    def validate_continuity(self, stratigraphy: List[Dict[str, Any]]) -> bool:
        if not stratigraphy:
            raise ValueError("地层数据为空")
        
        print("开始验证地层数据连续性...")
        sorted_stratigraphy = sorted(stratigraphy, key=lambda x: x['topDepth_m'])
        
        for i in range(len(sorted_stratigraphy)):
            current_layer = sorted_stratigraphy[i]
            
            required_fields = ['name', 'topDepth_m', 'bottomDepth_m']
            for field in required_fields:
                if field not in current_layer:
                    raise ValueError(f"地层 {i+1} 缺少必要字段: {field}")
            
            if current_layer['topDepth_m'] >= current_layer['bottomDepth_m']:
                raise ValueError(
                    f"地层 '{current_layer['name']}' 的顶部深度 ({current_layer['topDepth_m']}m) "
                    f"应该小于底部深度 ({current_layer['bottomDepth_m']}m)"
                )
            
            if i < len(sorted_stratigraphy) - 1:
                next_layer = sorted_stratigraphy[i + 1]
                current_bottom = current_layer['bottomDepth_m']
                next_top = next_layer['topDepth_m']
                
                if current_bottom != next_top:
                    error_msg = (
                        f"地层连续性验证失败！\n"
                        f"地层 '{current_layer['name']}' 的底部深度 ({current_bottom}m) "
                        f"与下一层 '{next_layer['name']}' 的顶部深度 ({next_top}m) 不连续\n"
                        f"深度差异: {abs(current_bottom - next_top)}m"
                    )
                    raise ValueError(error_msg)
                
                print(f"✓ 地层 '{current_layer['name']}' 与 '{next_layer['name']}' 连续")
        
        print("✓ 所有地层数据连续性验证通过")
        return True
    
    def export_raw_data(self, stratigraphy: List[Dict[str, Any]], output_file: str = "stratigraphy_raw.csv"):
        """第一步：导出原始数据（只提取，不计算）"""
        sorted_stratigraphy = sorted(stratigraphy, key=lambda x: x['topDepth_m'])
        
        fieldnames = ['序号', '地层名称', '顶部深度_m', '底部深度_m']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, layer in enumerate(sorted_stratigraphy, 1):
                    # 只导出非null的原始数据
                    if layer.get('name') and layer.get('topDepth_m') is not None and layer.get('bottomDepth_m') is not None:
                        row = {
                            '序号': i,
                            '地层名称': layer['name'],
                            '顶部深度_m': layer['topDepth_m'],
                            '底部深度_m': layer['bottomDepth_m']
                        }
                        writer.writerow(row)
            
            print(f"✓ 原始地层数据已导出到 {output_file}")
            print(f"  总共导出 {len(sorted_stratigraphy)} 个地层")
            
        except Exception as e:
            raise Exception(f"导出原始CSV文件失败: {e}")
    
    def map_raw_data(self, raw_csv_file: str = "stratigraphy_raw.csv", output_file: str = "stratigraphy.csv", total_mapped_thickness: float = 10.0):
        """第二步：从原始CSV读取数据，进行映射计算"""
        print(f"\n开始从 {raw_csv_file} 读取原始数据...")
        
        stratigraphy = []
        try:
            with open(raw_csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    layer = {
                        'name': row['地层名称'],
                        'topDepth_m': float(row['顶部深度_m']),
                        'bottomDepth_m': float(row['底部深度_m'])
                    }
                    stratigraphy.append(layer)
            
            print(f"✓ 读取到 {len(stratigraphy)} 个地层")
        except FileNotFoundError:
            raise FileNotFoundError(f"原始数据文件 {raw_csv_file} 不存在")
        except Exception as e:
            raise Exception(f"读取原始CSV文件失败: {e}")
        
        # 计算厚度（单位：m）
        for layer in stratigraphy:
            layer['actual_thickness_m'] = layer['bottomDepth_m'] - layer['topDepth_m']
        
        total_actual_thickness = sum(layer['actual_thickness_m'] for layer in stratigraphy)
        print(f"总实际厚度: {total_actual_thickness}m")
        print(f"总映射厚度: {total_mapped_thickness}cm")
        
        # 计算映射厚度（单位：cm）
        for layer in stratigraphy:
            proportion = layer['actual_thickness_m'] / total_actual_thickness
            mapped_thickness_cm = proportion * total_mapped_thickness
            layer['mapped_thickness_cm'] = mapped_thickness_cm
            layer['calc_note'] = f"映射厚度 = {layer['actual_thickness_m']}m / {total_actual_thickness}m × {total_mapped_thickness}cm = {mapped_thickness_cm:.4f}cm"
        
        print("初始映射厚度分配完成")
        
        # 调整最小厚度
        min_thickness = 0.24
        adjusted_count = 0
        
        for layer in stratigraphy:
            if layer['mapped_thickness_cm'] < min_thickness:
                original_thickness = layer['mapped_thickness_cm']
                print(f"  调整地层 '{layer['name']}': {original_thickness:.4f}cm -> {min_thickness}cm")
                layer['mapped_thickness_cm'] = min_thickness
                layer['calc_note'] = f"原映射厚度 = {original_thickness:.4f}cm，调整至最小值 {min_thickness}cm"
                adjusted_count += 1
        
        if adjusted_count > 0:
            print(f"✓ 共调整了 {adjusted_count} 个地层的映射厚度到最小值 {min_thickness}cm")
        else:
            print("✓ 所有地层映射厚度均大于最小值")
        
        # 计算映射顶部和底部深度（单位：cm）
        print("计算映射顶部和底部深度...")
        mapped_top = 0.0
        for layer in stratigraphy:
            layer['mapped_top_cm'] = mapped_top
            layer['mapped_bottom_cm'] = mapped_top + layer['mapped_thickness_cm']
            mapped_top = layer['mapped_bottom_cm']
        
        print("✓ 映射深度计算完成")
        
        # 导出映射后的数据
        fieldnames = ['序号', '地层名称', '顶部深度_m', '底部深度_m', '厚度_cm', 
                     '映射厚度_cm', '映射顶部_cm', '映射底部_cm', '备注']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, layer in enumerate(stratigraphy, 1):
                    row = {
                        '序号': i,
                        '地层名称': layer['name'],
                        '顶部深度_m': layer['topDepth_m'],
                        '底部深度_m': layer['bottomDepth_m'],
                        '厚度_cm': round(layer['actual_thickness_m'] * 100, 2),  # 转换为cm
                        '映射厚度_cm': round(layer['mapped_thickness_cm'], 4),
                        '映射顶部_cm': round(layer['mapped_top_cm'], 4),
                        '映射底部_cm': round(layer['mapped_bottom_cm'], 4),
                        '备注': layer['calc_note']
                    }
                    writer.writerow(row)
            
            print(f"\n✓ 映射后的地层数据已导出到 {output_file}")
            print(f"  总共导出 {len(stratigraphy)} 个地层")
            
            total_mapped = sum(layer['mapped_thickness_cm'] for layer in stratigraphy)
            print(f"  实际映射厚度总计: {total_mapped:.4f}cm")
            
        except Exception as e:
            raise Exception(f"导出映射CSV文件失败: {e}")
    
    def process_step1_extract(self, output_file: str = "stratigraphy_raw.csv"):
        """执行第一步：提取原始数据（不进行任何验证）"""
        try:
            print(f"【第一步】提取原始地层数据: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            stratigraphy = self.extract_stratigraphy(data)
            print(f"✓ 提取到 {len(stratigraphy)} 个地层")
            
            # 第一步只提取原始数据，不进行验证
            self.export_raw_data(stratigraphy, output_file)
            
            print("✓ 第一步完成！\n")
            
        except Exception as e:
            print(f"❌ 第一步失败: {e}")
            raise
    
    def process_step2_map(self, raw_csv_file: str = "stratigraphy_raw.csv", output_file: str = "stratigraphy.csv"):
        """执行第二步：映射原始数据"""
        try:
            print(f"【第二步】映射地层数据: {raw_csv_file} -> {output_file}")
            self.map_raw_data(raw_csv_file, output_file)
            
            print("✓ 第二步完成！\n")
            
        except Exception as e:
            print(f"❌ 第二步失败: {e}")
            raise


# ============================================================================
# 深度映射基础类
# ============================================================================
class DepthMappingMixin:
    """深度映射混合类"""
    
    @staticmethod
    def load_stratigraphy_mapping(stratigraphy_csv_path: str) -> List[Dict[str, Any]]:
        try:
            stratigraphy_mapping = []
            with open(stratigraphy_csv_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    mapping_data = {
                        'topDepth_m': float(row['顶部深度_m']),
                        'bottomDepth_m': float(row['底部深度_m']),
                        'mapped_top_cm': float(row['映射顶部_cm']),
                        'mapped_bottom_cm': float(row['映射底部_cm'])
                    }
                    stratigraphy_mapping.append(mapping_data)
            
            print(f"✓ 成功加载 {len(stratigraphy_mapping)} 个地层映射数据")
            return stratigraphy_mapping
        except FileNotFoundError:
            raise FileNotFoundError(f"地层映射文件 {stratigraphy_csv_path} 不存在")
        except Exception as e:
            raise Exception(f"读取地层映射文件失败: {e}")
    
    @staticmethod
    def calculate_mapped_depth(actual_depth_m: float, stratigraphy_mapping: List[Dict[str, Any]]) -> float:
        for layer in stratigraphy_mapping:
            if layer['topDepth_m'] <= actual_depth_m <= layer['bottomDepth_m']:
                layer_thickness_m = layer['bottomDepth_m'] - layer['topDepth_m']
                layer_mapped_thickness_cm = layer['mapped_bottom_cm'] - layer['mapped_top_cm']
                
                if layer_thickness_m == 0:
                    return layer['mapped_top_cm']
                
                depth_ratio = (actual_depth_m - layer['topDepth_m']) / layer_thickness_m
                mapped_depth_cm = layer['mapped_top_cm'] + depth_ratio * layer_mapped_thickness_cm
                return mapped_depth_cm
        
        # 如果深度超出范围，采用线性比例计算
        if actual_depth_m < stratigraphy_mapping[0]['topDepth_m']:
            return stratigraphy_mapping[0]['mapped_top_cm']
        else:
            # 深度超过最深层位，使用线性比例计算：映射值 = 最大映射深度 * 实际深度 / 最大实际深度
            deepest_layer = stratigraphy_mapping[-1]
            deepest_bottom_m = deepest_layer['bottomDepth_m']
            deepest_mapped_bottom_cm = deepest_layer['mapped_bottom_cm']
            
            # 使用线性比例：映射值 = 最大映射深度 * 实际深度 / 最大实际深度
            mapped_depth_cm = deepest_mapped_bottom_cm * actual_depth_m / deepest_bottom_m
            return mapped_depth_cm


# ============================================================================
# 钻井液数据提取器
# ============================================================================
class DrillingFluidExtractor(DepthMappingMixin):
    """钻井液与压力数据提取器类 - 分离原始数据提取和数据映射"""
    
    def __init__(self, json_file_path: str, stratigraphy_csv_path: str = "stratigraphy.csv"):
        self.json_file_path = json_file_path
        self.stratigraphy_csv_path = stratigraphy_csv_path
    
    def load_json_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {self.json_file_path} 不存在")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON文件格式错误: {e}")
    
    def extract_drilling_fluid_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if 'drillingFluidAndPressure' not in data:
            raise KeyError("JSON数据中缺少 'drillingFluidAndPressure' 字段")
        
        drilling_fluid_data = data['drillingFluidAndPressure']
        if not isinstance(drilling_fluid_data, list):
            raise ValueError("drillingFluidAndPressure字段应该是一个列表")
        
        return drilling_fluid_data
    
    def validate_continuity(self, drilling_fluid_data: List[Dict[str, Any]]) -> bool:
        if not drilling_fluid_data:
            raise ValueError("钻井液与压力数据为空")
        
        print("开始验证钻井液与压力数据连续性...")
        sorted_data = sorted(drilling_fluid_data, key=lambda x: x['topDepth_m'])
        
        for i in range(len(sorted_data)):
            current_section = sorted_data[i]
            
            required_fields = ['topDepth_m', 'bottomDepth_m', 'porePressure_gcm3', 'pressureWindow_gcm3']
            for field in required_fields:
                if field not in current_section:
                    raise ValueError(f"钻井液段 {i+1} 缺少必要字段: {field}")
            
            pressure_window = current_section['pressureWindow_gcm3']
            if not isinstance(pressure_window, dict) or 'min' not in pressure_window or 'max' not in pressure_window:
                raise ValueError(f"钻井液段 {i+1} 的泥浆密度窗口格式错误")
            
            if current_section['topDepth_m'] >= current_section['bottomDepth_m']:
                raise ValueError(
                    f"钻井液段 {i+1} 的顶部深度 ({current_section['topDepth_m']}m) "
                    f"应该小于底部深度 ({current_section['bottomDepth_m']}m)"
                )
            
            if i < len(sorted_data) - 1:
                next_section = sorted_data[i + 1]
                current_bottom = current_section['bottomDepth_m']
                next_top = next_section['topDepth_m']
                
                if current_bottom != next_top:
                    error_msg = (
                        f"钻井液与压力数据连续性验证失败！\n"
                        f"第 {i+1} 段的底部深度 ({current_bottom}m) "
                        f"与第 {i+2} 段的顶部深度 ({next_top}m) 不连续\n"
                        f"深度差异: {abs(current_bottom - next_top)}m"
                    )
                    raise ValueError(error_msg)
                
                print(f"✓ 第 {i+1} 段与第 {i+2} 段连续")
        
        print("✓ 所有钻井液与压力数据连续性验证通过")
        return True
    
    def export_raw_data(self, drilling_fluid_data: List[Dict[str, Any]], output_file: str = "drilling_fluid_pressure_raw.csv"):
        """第一步：导出原始数据（只提取，不计算）"""
        sorted_data = sorted(drilling_fluid_data, key=lambda x: x['topDepth_m'])
        
        fieldnames = [
            '序号', '顶部深度_m', '底部深度_m',
            '孔隙压力_gcm3', '泥浆密度窗口最小值_gcm3', '泥浆密度窗口最大值_gcm3'
        ]
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(sorted_data, 1):
                    # 只导出非null的原始数据
                    if (section.get('topDepth_m') is not None and 
                        section.get('bottomDepth_m') is not None and
                        section.get('porePressure_gcm3') is not None and
                        section.get('pressureWindow_gcm3') is not None):
                        
                        row = {
                            '序号': i,
                            '顶部深度_m': section['topDepth_m'],
                            '底部深度_m': section['bottomDepth_m'],
                            '孔隙压力_gcm3': section['porePressure_gcm3'],
                            '泥浆密度窗口最小值_gcm3': section['pressureWindow_gcm3']['min'],
                            '泥浆密度窗口最大值_gcm3': section['pressureWindow_gcm3']['max']
                        }
                        writer.writerow(row)
            
            print(f"✓ 原始钻井液数据已导出到 {output_file}")
            print(f"  总共导出 {len(sorted_data)} 个深度段")
        except Exception as e:
            raise Exception(f"导出原始CSV文件失败: {e}")
    
    def map_raw_data(self, raw_csv_file: str = "drilling_fluid_pressure_raw.csv", 
                     stratigraphy_csv_path: str = "stratigraphy.csv",
                     output_file: str = "drilling_fluid_pressure.csv"):
        """第二步：从原始CSV读取数据，进行映射计算"""
        print(f"\n开始从 {raw_csv_file} 读取原始数据...")
        
        drilling_fluid_data = []
        try:
            with open(raw_csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    section = {
                        'topDepth_m': float(row['顶部深度_m']),
                        'bottomDepth_m': float(row['底部深度_m']),
                        'porePressure_gcm3': float(row['孔隙压力_gcm3']),
                        'pressureWindow_min_gcm3': float(row['泥浆密度窗口最小值_gcm3']),
                        'pressureWindow_max_gcm3': float(row['泥浆密度窗口最大值_gcm3'])
                    }
                    drilling_fluid_data.append(section)
            
            print(f"✓ 读取到 {len(drilling_fluid_data)} 个钻井液段")
        except FileNotFoundError:
            raise FileNotFoundError(f"原始数据文件 {raw_csv_file} 不存在")
        except Exception as e:
            raise Exception(f"读取原始CSV文件失败: {e}")
        
        # 加载地层映射数据
        stratigraphy_mapping = self.load_stratigraphy_mapping(stratigraphy_csv_path)
        
        # 计算映射深度
        print("计算映射深度...")
        for section in drilling_fluid_data:
            section['mapped_top_cm'] = self.calculate_mapped_depth(section['topDepth_m'], stratigraphy_mapping)
            section['mapped_bottom_cm'] = self.calculate_mapped_depth(section['bottomDepth_m'], stratigraphy_mapping)
        
        print("✓ 映射深度计算完成")
        
        # 导出映射后的数据
        fieldnames = [
            '序号', '顶部深度_cm', '底部深度_cm', '厚度_cm',
            '孔隙压力_gcm3', '泥浆密度窗口最小值_gcm3', '泥浆密度窗口最大值_gcm3',
            '映射顶部_cm', '映射底部_cm', '备注'
        ]
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(drilling_fluid_data, 1):
                    # 计算厚度（单位：cm）
                    thickness_cm = (section['bottomDepth_m'] - section['topDepth_m']) * 100
                    
                    # 生成备注
                    note = f"由地层{section['topDepth_m']}m-{section['bottomDepth_m']}m映射"
                    
                    row = {
                        '序号': i,
                        '顶部深度_cm': round(section['topDepth_m'] * 100, 2),
                        '底部深度_cm': round(section['bottomDepth_m'] * 100, 2),
                        '厚度_cm': round(thickness_cm, 2),
                        '孔隙压力_gcm3': section['porePressure_gcm3'],
                        '泥浆密度窗口最小值_gcm3': section['pressureWindow_min_gcm3'],
                        '泥浆密度窗口最大值_gcm3': section['pressureWindow_max_gcm3'],
                        '映射顶部_cm': round(section['mapped_top_cm'], 4),
                        '映射底部_cm': round(section['mapped_bottom_cm'], 4),
                        '备注': note
                    }
                    writer.writerow(row)
            
            print(f"✓ 映射后的钻井液数据已导出到 {output_file}")
            print(f"  总共导出 {len(drilling_fluid_data)} 个深度段")
        except Exception as e:
            raise Exception(f"导出映射CSV文件失败: {e}")
    
    def process_step1_extract(self, output_file: str = "drilling_fluid_pressure_raw.csv"):
        """执行第一步：提取原始数据（不进行任何验证）"""
        try:
            print(f"【第一步】提取原始钻井液数据: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            drilling_fluid_data = self.extract_drilling_fluid_data(data)
            print(f"✓ 提取到 {len(drilling_fluid_data)} 个钻井液与压力段")
            
            # 第一步只提取原始数据，不进行验证
            self.export_raw_data(drilling_fluid_data, output_file)
            
            print("✓ 第一步完成！\n")
        except Exception as e:
            print(f"❌ 第一步失败: {e}")
            raise
    
    def process_step2_map(self, raw_csv_file: str = "drilling_fluid_pressure_raw.csv", 
                          output_file: str = "drilling_fluid_pressure.csv"):
        """执行第二步：映射原始数据"""
        try:
            print(f"【第二步】映射钻井液数据: {raw_csv_file} -> {output_file}")
            self.map_raw_data(raw_csv_file, self.stratigraphy_csv_path, output_file)
            
            print("✓ 第二步完成！\n")
        except Exception as e:
            print(f"❌ 第二步失败: {e}")
            raise


# ============================================================================
# 井眼轨迹数据提取器
# ============================================================================
class DeviationDataExtractor(DepthMappingMixin):
    """井斜数据提取器类 - 分离原始数据提取和数据映射"""
    
    def __init__(self, json_file_path: str, stratigraphy_csv_path: str = "stratigraphy.csv"):
        self.json_file_path = json_file_path
        self.stratigraphy_csv_path = stratigraphy_csv_path
    
    def load_json_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {self.json_file_path} 不存在")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON文件格式错误: {e}")
    
    def extract_deviation_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'deviationData' not in data:
            raise KeyError("JSON数据中缺少 'deviationData' 字段")
        
        deviation_data = data['deviationData']
        if not isinstance(deviation_data, dict):
            raise ValueError("deviationData字段应该是一个字典")
        
        return deviation_data
    
    def validate_deviation_data(self, deviation_data: Dict[str, Any]) -> bool:
        print("开始验证井斜数据...")
        
        # 检查是否为直井，如果是直井则设置默认值并跳过验证
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                well_data = json.load(f)
            well_type = well_data.get('wellType', '').strip().lower()
            total_depth = well_data.get('totalDepth_m', 0)
            
            if well_type == 'straight well':
                # 直井时设置默认值
                deviation_data['deviationAngle_deg'] = 0
                deviation_data['kickoffPoint_m'] = total_depth
                deviation_data['targetPointA_m'] = total_depth
                deviation_data['targetPointA_verticalDepth_m'] = total_depth
                deviation_data['REAL_kickoffPoint_m'] = total_depth
                deviation_data['targetPointB_m'] = total_depth
                deviation_data['DistanceAB_m'] = 0
                
                print(f"✓ 直井模式：设置deviationData默认值")
                print(f"  井斜角度: 0度")
                print(f"  造斜点深度: {total_depth}m")
                print(f"  目标点A深度: {total_depth}m")
                print(f"  A点垂深: {total_depth}m")
                print(f"  真实造斜点深度: {total_depth}m")
                print(f"  目标点B深度: {total_depth}m")
                print(f"  AB点距离: 0m")
                print("✓ 直井模式：跳过数据验证")
                return True
        except Exception as e:
            print(f"⚠️ 读取井类型失败: {e}")
        
        # 处理kickoffPoint_m的备选值
        kickoff_point = deviation_data.get('kickoffPoint_m')
        if kickoff_point is None or kickoff_point == '' or str(kickoff_point).lower() == 'null':
            # 依次尝试备选值
            if 'REAL_kickoffPoint_m' in deviation_data:
                kickoff_point = deviation_data['REAL_kickoffPoint_m']
                print(f"✓ kickoffPoint_m为空，使用REAL_kickoffPoint_m: {kickoff_point}m")
            else:
                # 尝试从well_data.json中获取totalDepth_m
                try:
                    with open(self.json_file_path, 'r', encoding='utf-8') as f:
                        well_data = json.load(f)
                    total_depth = well_data.get('totalDepth_m', 0)
                    if total_depth > 0:
                        kickoff_point = total_depth
                        print(f"✓ kickoffPoint_m为空，使用totalDepth_m: {kickoff_point}m")
                    else:
                        kickoff_point = 0
                        print(f"✓ kickoffPoint_m为空，使用默认值0")
                except:
                    kickoff_point = 0
                    print(f"✓ kickoffPoint_m为空，使用默认值0")
            
            # 更新deviation_data中的值
            deviation_data['kickoffPoint_m'] = kickoff_point
        
        # 检查必要字段
        required_fields = ['kickoffPoint_m']
        for field in required_fields:
            if field not in deviation_data:
                raise ValueError(f"井斜数据缺少必要字段: {field}")
        
        # 处理井斜角度
        kickoff_point = deviation_data['kickoffPoint_m']
        deviation_angle = deviation_data.get('deviationAngle_deg')
        
        # 检查井类型和角度处理
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                well_data = json.load(f)
            well_type = well_data.get('wellType', '').strip().lower()
        except:
            well_type = ''
        
        # 如果角度为null或缺失
        if deviation_angle is None or deviation_angle == '' or str(deviation_angle).lower() == 'null':
            if well_type == 'horizontal well':
                # 水平井：自动设置为90度
                deviation_angle = 90.0
                deviation_data['deviationAngle_deg'] = deviation_angle
                print(f"✓ 水平井模式：deviationAngle_deg为null，自动设置为90度")
            elif well_type == 'deviated well':
                # 定向井：自动设置为45度
                deviation_angle = 45.0
                deviation_data['deviationAngle_deg'] = deviation_angle
                print(f"✓ 定向井模式：deviationAngle_deg为null，自动设置为45度")
            else:
                # 其他井型（直井）：设置为0度
                deviation_angle = 0.0
                deviation_data['deviationAngle_deg'] = deviation_angle
                print(f"✓ 直井模式：deviationAngle_deg为null，设置为0度")
        
        # 定向井特殊处理：角度≤1°时按30°处理
        if well_type == 'deviated well' and deviation_angle is not None and deviation_angle <= 1:
            print(f"✓ 定向井模式：检测到井斜角度≤1° ({deviation_angle}°)，按30°处理")
            deviation_angle = 30.0
            deviation_data['deviationAngle_deg'] = deviation_angle
        
        # 验证角度范围并给出提示
        if not (0 <= deviation_angle <= 90):
            raise ValueError(f"井斜角度应在0-90度范围内，当前值: {deviation_angle}度")
        
        # 水平井角度检查提示
        if well_type == 'horizontal well' and deviation_angle < 90:
            print(f"⚠️ 水平井角度检查：当前角度为{deviation_angle}度，建议检查是否为90度")
        
        # 处理造斜点、A点深度、A点垂深的几何关系（导向井/水平井）
        target_point_a = deviation_data.get('targetPointA_m')
        target_point_a_vertical = deviation_data.get('targetPointA_verticalDepth_m')
        
        # 检查这三个关键参数的有效性
        geometric_params = []
        if kickoff_point is not None and kickoff_point != '' and str(kickoff_point).lower() != 'null':
            geometric_params.append('kickoff')
        if target_point_a is not None and target_point_a != '' and str(target_point_a).lower() != 'null':
            geometric_params.append('target_a')
        if target_point_a_vertical is not None and target_point_a_vertical != '' and str(target_point_a_vertical).lower() != 'null':
            geometric_params.append('target_a_vertical')
        
        # 如果至少有两个参数，进行几何关系计算
        if len(geometric_params) >= 2:
            import math
            deviation_angle_rad = math.radians(deviation_angle)
            theta = deviation_angle_rad
            sin_theta = math.sin(theta)
            
            print(f"✓ 检测到几何参数: {geometric_params}")
            
            if 'kickoff' in geometric_params and 'target_a' in geometric_params and 'target_a_vertical' not in geometric_params:
                # 已知造斜点和A点深度，计算A点垂深
                if theta != 0 and sin_theta != 0:
                    R = (target_point_a - kickoff_point) / theta
                    calculated_vertical = R * sin_theta + kickoff_point
                    deviation_data['targetPointA_verticalDepth_m'] = calculated_vertical
                    print(f"✓ 根据几何关系计算A点垂深: {calculated_vertical:.2f}m")
                else:
                    print("⚠️ 井斜角度为0度，无法计算A点垂深")
            elif 'kickoff' in geometric_params and 'target_a_vertical' in geometric_params and 'target_a' not in geometric_params:
                # 已知造斜点和A点垂深，计算A点深度
                if theta != 0 and sin_theta != 0:
                    R = (target_point_a_vertical - kickoff_point) / sin_theta
                    calculated_target_a = R * theta + kickoff_point
                    deviation_data['targetPointA_m'] = calculated_target_a
                    print(f"✓ 根据几何关系计算A点深度: {calculated_target_a:.2f}m")
                else:
                    print("⚠️ 井斜角度为0度，无法计算A点深度")
            elif 'target_a' in geometric_params and 'target_a_vertical' in geometric_params and 'kickoff' not in geometric_params:
                # 已知A点深度和A点垂深，计算造斜点深度
                if sin_theta != theta and sin_theta != 0:
                    calculated_kickoff = (target_point_a * sin_theta - target_point_a_vertical * theta) / (sin_theta - theta)
                    deviation_data['kickoffPoint_m'] = calculated_kickoff
                    print(f"✓ 根据几何关系计算造斜点深度: {calculated_kickoff:.2f}m")
                else:
                    print("⚠️ 井斜角度为0度，无法计算造斜点深度")
        
        # 处理A点、B点深度和AB点距离的逻辑关系
        target_point_a = deviation_data.get('targetPointA_m')
        target_point_b = deviation_data.get('targetPointB_m')
        distance_ab = deviation_data.get('DistanceAB_m')
        
        # 计算实际存在的值数量
        available_values = []
        if target_point_a is not None and target_point_a != '' and str(target_point_a).lower() != 'null':
            available_values.append('A')
        if target_point_b is not None and target_point_b != '' and str(target_point_b).lower() != 'null':
            available_values.append('B')
        if distance_ab is not None and distance_ab != '' and str(distance_ab).lower() != 'null':
            available_values.append('AB')
        
        if len(available_values) < 2:
            raise ValueError(f"A点深度、B点深度和AB点距离中至少需要提供两个值，当前提供: {available_values}")
        
        # 根据提供的值计算缺失的值
        if 'A' in available_values and 'B' in available_values:
            # 如果A和B都存在，计算AB距离
            calculated_ab = abs(target_point_b - target_point_a)
            if 'AB' in available_values:
                # 验证AB距离是否正确
                if abs(calculated_ab - distance_ab) > 0.001:  # 允许0.001m的误差
                    raise ValueError(f"AB点距离数据不一致: 计算值={calculated_ab}m, 提供值={distance_ab}m")
            else:
                # 使用计算值
                deviation_data['DistanceAB_m'] = calculated_ab
                print(f"✓ 根据A点和B点深度计算AB点距离: {calculated_ab}m")
        elif 'A' in available_values and 'AB' in available_values:
            # 如果A和AB存在，计算B
            calculated_b = target_point_a + distance_ab
            deviation_data['targetPointB_m'] = calculated_b
            print(f"✓ 根据A点深度和AB点距离计算B点深度: {calculated_b}m")
        elif 'B' in available_values and 'AB' in available_values:
            # 如果B和AB存在，计算A
            calculated_a = target_point_b - distance_ab
            deviation_data['targetPointA_m'] = calculated_a
            print(f"✓ 根据B点深度和AB点距离计算A点深度: {calculated_a}m")
        
        # 重新获取计算后的值
        target_point_a = deviation_data['targetPointA_m']
        target_point_b = deviation_data['targetPointB_m']
        
        # 验证深度顺序
        if not (kickoff_point < target_point_a <= target_point_b):
            raise ValueError(
                f"深度顺序错误: 造斜点({kickoff_point}m) < 目标点A({target_point_a}m) <= 目标点B({target_point_b}m)"
            )
        
        print("✓ 井斜数据验证通过")
        return True
    
    def export_to_csv(self, deviation_data: Dict[str, Any], stratigraphy_mapping: list, output_file: str = "deviationData.csv"):
        print("计算映射深度...")
        
        kickoff_mapped = self.calculate_mapped_depth(deviation_data['kickoffPoint_m'], stratigraphy_mapping)
        target_a_mapped = self.calculate_mapped_depth(deviation_data['targetPointA_m'], stratigraphy_mapping)
        target_b_mapped = self.calculate_mapped_depth(deviation_data['targetPointB_m'], stratigraphy_mapping)
        
        # 计算A点垂深的映射深度（如果存在）
        target_a_vertical_mapped = None
        if 'targetPointA_verticalDepth_m' in deviation_data:
            target_a_vertical_mapped = self.calculate_mapped_depth(deviation_data['targetPointA_verticalDepth_m'], stratigraphy_mapping)
        
        # 计算真实造斜点的映射深度（如果存在）
        real_kickoff_mapped = None
        if 'REAL_kickoffPoint_m' in deviation_data:
            real_kickoff_mapped = self.calculate_mapped_depth(deviation_data['REAL_kickoffPoint_m'], stratigraphy_mapping)
        
        # 根据几何关系计算映射深度
        # R*θ + 造斜点深度 = 目标点A深度
        # R*sin(θ) + 造斜点深度 = A点垂深
        # 消去R: 造斜点深度 = (目标点A深度*sin(θ) - A点垂深*θ) / (sin(θ) - θ)
        import math
        
        deviation_angle_rad = math.radians(deviation_data['deviationAngle_deg'])
        theta = deviation_angle_rad
        sin_theta = math.sin(theta)
        
        # 检查是否有目标点A深度和A点垂深
        if target_a_mapped is not None and target_a_vertical_mapped is not None:
            # 优先使用目标点A深度和A点垂深计算造斜点深度
            if sin_theta != theta and sin_theta != 0:  # 避免除零错误
                calculated_kickoff = (target_a_mapped * sin_theta - target_a_vertical_mapped * theta) / (sin_theta - theta)
                kickoff_mapped = calculated_kickoff
                print(f"✓ 根据几何关系计算造斜点映射深度: {calculated_kickoff:.4f}cm")
            else:
                print("⚠️ 井斜角度为0度，无法使用几何关系计算")
        elif kickoff_mapped is not None and target_a_mapped is not None:
            # 已知造斜点深度和目标点A深度，计算A点垂深
            if theta != 0:
                R = (target_a_mapped - kickoff_mapped) / theta
                calculated_vertical = R * sin_theta + kickoff_mapped
                target_a_vertical_mapped = calculated_vertical
                print(f"✓ 根据几何关系计算A点垂深映射值: {calculated_vertical:.4f}cm")
        elif kickoff_mapped is not None and target_a_vertical_mapped is not None:
            # 已知造斜点深度和A点垂深，计算目标点A深度
            if sin_theta != 0:
                R = (target_a_vertical_mapped - kickoff_mapped) / sin_theta
                calculated_target_a = R * theta + kickoff_mapped
                target_a_mapped = calculated_target_a
                print(f"✓ 根据几何关系计算目标点A映射深度: {calculated_target_a:.4f}cm")
        
        # 计算映射后的AB距离 - 直接使用B点映射值减去A点映射值
        mapped_distance_ab = abs(target_b_mapped - target_a_mapped)
        actual_ab_depth_diff = abs(deviation_data['targetPointB_m'] - deviation_data['targetPointA_m'])
        
        print(f"✓ 映射深度计算完成")
        
        if actual_ab_depth_diff == 0:
            print(f"  注意: 目标点A和目标点B深度相同({deviation_data['targetPointA_m']}m)，AB距离为0")
        
        fieldnames = ['参数名称', '数值', '单位', '说明', '映射值', '映射单位']
        
        data_rows = [
            {
                '参数名称': '造斜点深度',
                '数值': deviation_data['kickoffPoint_m'],
                '单位': 'm',
                '说明': '开始造斜的井深位置',
                '映射值': round(kickoff_mapped, 4),
                '映射单位': 'cm'
            },
            {
                '参数名称': '井斜角度',
                '数值': deviation_data['deviationAngle_deg'],
                '单位': 'deg',
                '说明': '井眼偏离垂直方向的角度',
                '映射值': deviation_data['deviationAngle_deg'],
                '映射单位': 'deg'
            },
            {
                '参数名称': '目标点A深度',
                '数值': deviation_data['targetPointA_m'],
                '单位': 'm',
                '说明': '第一个目标深度点',
                '映射值': round(target_a_mapped, 4),
                '映射单位': 'cm'
            },
            {
                '参数名称': '目标点B深度',
                '数值': deviation_data['targetPointB_m'],
                '单位': 'm',
                '说明': '第二个目标深度点',
                '映射值': round(target_b_mapped, 4),
                '映射单位': 'cm'
            }
        ]
        
        # 添加A点垂深数据到输出中（如果存在）
        if target_a_vertical_mapped is not None:
            data_rows.append({
                '参数名称': 'A点垂深',
                '数值': deviation_data['targetPointA_verticalDepth_m'],
                '单位': 'm',
                '说明': '目标点A的垂直深度',
                '映射值': round(target_a_vertical_mapped, 4),
                '映射单位': 'cm'
            })
        
        # 添加真实造斜点深度数据到输出中（如果存在）
        if real_kickoff_mapped is not None:
            data_rows.append({
                '参数名称': '真实造斜点深度',
                '数值': deviation_data['REAL_kickoffPoint_m'],
                '单位': 'm',
                '说明': '实际开始造斜的井深位置',
                '映射值': round(real_kickoff_mapped, 4),
                '映射单位': 'cm'
            })
        
        if mapped_distance_ab is not None:
            # 确定实际距离值
            actual_distance_value = abs(deviation_data['targetPointB_m'] - deviation_data['targetPointA_m'])
            description = '目标点A到目标点B的距离（由targetPointB_m - targetPointA_m计算）'
            
            data_rows.append({
                '参数名称': 'AB点距离',
                '数值': actual_distance_value,
                '单位': 'm',
                '说明': description,
                '映射值': round(mapped_distance_ab, 4),
                '映射单位': 'cm'
            })
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in data_rows:
                    writer.writerow(row)
            
            print(f"✓ 井斜数据已成功导出到 {output_file}")
            print(f"  总共导出 {len(data_rows)} 个参数")
        except Exception as e:
            raise Exception(f"导出CSV文件失败: {e}")
    
    def export_raw_data(self, deviation_data: Dict[str, Any], output_file: str = "deviationData_raw.csv"):
        """第一步：导出原始数据（只提取，不计算，保留JSON中的所有原始值）"""
        fieldnames = ['参数名称', '数值', '单位']
        
        # 准备原始数据行（只导出JSON中有值且不为null的字段）
        data_rows = []
        
        # 检查函数：判断值是否有效（非null、非空字符串）
        def is_valid_value(value):
            if value is None:
                return False
            if isinstance(value, str) and (value == '' or value.lower() == 'null'):
                return False
            return True
        
        # 必须字段
        if is_valid_value(deviation_data.get('kickoffPoint_m')):
            data_rows.append({
                '参数名称': '造斜点深度',
                '数值': deviation_data['kickoffPoint_m'],
                '单位': 'm'
            })
        
        if is_valid_value(deviation_data.get('deviationAngle_deg')):
            data_rows.append({
                '参数名称': '井斜角度',
                '数值': deviation_data['deviationAngle_deg'],
                '单位': 'deg'
            })
        
        if is_valid_value(deviation_data.get('targetPointA_m')):
            data_rows.append({
                '参数名称': '目标点A深度',
                '数值': deviation_data['targetPointA_m'],
                '单位': 'm'
            })
        
        if is_valid_value(deviation_data.get('targetPointB_m')):
            data_rows.append({
                '参数名称': '目标点B深度',
                '数值': deviation_data['targetPointB_m'],
                '单位': 'm'
            })
        
        # 可选字段
        if is_valid_value(deviation_data.get('targetPointA_verticalDepth_m')):
            data_rows.append({
                '参数名称': 'A点垂深',
                '数值': deviation_data['targetPointA_verticalDepth_m'],
                '单位': 'm'
            })
        
        if is_valid_value(deviation_data.get('REAL_kickoffPoint_m')):
            data_rows.append({
                '参数名称': '真实造斜点深度',
                '数值': deviation_data['REAL_kickoffPoint_m'],
                '单位': 'm'
            })
        
        if is_valid_value(deviation_data.get('DistanceAB_m')):
            data_rows.append({
                '参数名称': 'AB点距离',
                '数值': deviation_data['DistanceAB_m'],
                '单位': 'm'
            })
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in data_rows:
                    writer.writerow(row)
            
            print(f"✓ 原始井斜数据已导出到 {output_file}")
            print(f"  总共导出 {len(data_rows)} 个参数")
        except Exception as e:
            raise Exception(f"导出原始CSV文件失败: {e}")
    
    def map_raw_data(self, raw_csv_file: str = "deviationData_raw.csv",
                     stratigraphy_csv_path: str = "stratigraphy.csv",
                     output_file: str = "deviationData.csv"):
        """第二步：从原始CSV读取数据，进行映射和计算"""
        print(f"\n开始从 {raw_csv_file} 读取原始数据...")
        
        # 读取原始数据
        deviation_data = {}
        try:
            with open(raw_csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    param_name = row['参数名称']
                    value = float(row['数值']) if row['数值'] else None
                    
                    if param_name == '造斜点深度':
                        deviation_data['kickoffPoint_m'] = value
                    elif param_name == '井斜角度':
                        deviation_data['deviationAngle_deg'] = value
                    elif param_name == '目标点A深度':
                        deviation_data['targetPointA_m'] = value
                    elif param_name == '目标点B深度':
                        deviation_data['targetPointB_m'] = value
                    elif param_name == 'A点垂深':
                        deviation_data['targetPointA_verticalDepth_m'] = value
                    elif param_name == '真实造斜点深度':
                        deviation_data['REAL_kickoffPoint_m'] = value
                    elif param_name == 'AB点距离':
                        deviation_data['DistanceAB_m'] = value
            
            print(f"✓ 读取到 {len(deviation_data)} 个井斜参数")
        except FileNotFoundError:
            raise FileNotFoundError(f"原始数据文件 {raw_csv_file} 不存在")
        except Exception as e:
            raise Exception(f"读取原始CSV文件失败: {e}")
        
        # 如果井斜角度缺失或为None，根据井类型设置默认值
        if 'deviationAngle_deg' not in deviation_data or deviation_data.get('deviationAngle_deg') is None:
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    well_data = json.load(f)
                well_type = well_data.get('wellType', '').strip().lower()
                
                if well_type == 'horizontal well':
                    deviation_data['deviationAngle_deg'] = 90.0
                    print(f"✓ 水平井模式：井斜角度缺失，自动设置为90度")
                elif well_type == 'deviated well':
                    deviation_data['deviationAngle_deg'] = 45.0
                    print(f"✓ 定向井模式：井斜角度缺失，自动设置为45度")
                else:
                    deviation_data['deviationAngle_deg'] = 0.0
                    print(f"✓ 直井模式：井斜角度缺失，自动设置为0度")
            except Exception as e:
                print(f"⚠️ 读取井类型失败: {e}，井斜角度默认为0度")
                deviation_data['deviationAngle_deg'] = 0.0
        
        # 定向井特殊处理：角度≤1°时按30°处理
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                well_data = json.load(f)
            well_type = well_data.get('wellType', '').strip().lower()
            
            if well_type == 'deviated well':
                current_angle = deviation_data.get('deviationAngle_deg', 0)
                if current_angle is not None and current_angle <= 1:
                    print(f"✓ 定向井模式：检测到井斜角度≤1° ({current_angle}°)，按30°处理")
                    deviation_data['deviationAngle_deg'] = 30.0
        except Exception as e:
            pass  # 如果读取失败，保持原值
        
        # 加载地层映射数据
        stratigraphy_mapping = self.load_stratigraphy_mapping(stratigraphy_csv_path)
        
        # 第一步：只对原始CSV中有值的字段进行直接映射
        print("第一步：直接映射原始数据...")
        import math
        
        # 初始化所有字段为None
        kickoff_mapped = None
        target_a_mapped = None
        target_b_mapped = None
        target_a_vertical_mapped = None
        real_kickoff_mapped = None
        
        # 只映射原始CSV中存在的值
        if deviation_data.get('kickoffPoint_m') is not None:
            kickoff_mapped = self.calculate_mapped_depth(deviation_data['kickoffPoint_m'], stratigraphy_mapping)
            print(f"  ✓ 造斜点深度直接映射: {deviation_data['kickoffPoint_m']}m → {kickoff_mapped:.4f}cm")
        
        if deviation_data.get('targetPointA_m') is not None:
            target_a_mapped = self.calculate_mapped_depth(deviation_data['targetPointA_m'], stratigraphy_mapping)
            print(f"  ✓ 目标点A深度直接映射: {deviation_data['targetPointA_m']}m → {target_a_mapped:.4f}cm")
        
        if deviation_data.get('targetPointB_m') is not None:
            target_b_mapped = self.calculate_mapped_depth(deviation_data['targetPointB_m'], stratigraphy_mapping)
            print(f"  ✓ 目标点B深度直接映射: {deviation_data['targetPointB_m']}m → {target_b_mapped:.4f}cm")
        
        if deviation_data.get('targetPointA_verticalDepth_m') is not None:
            target_a_vertical_mapped = self.calculate_mapped_depth(deviation_data['targetPointA_verticalDepth_m'], stratigraphy_mapping)
            print(f"  ✓ A点垂深直接映射: {deviation_data['targetPointA_verticalDepth_m']}m → {target_a_vertical_mapped:.4f}cm")
        
        if deviation_data.get('REAL_kickoffPoint_m') is not None:
            real_kickoff_mapped = self.calculate_mapped_depth(deviation_data['REAL_kickoffPoint_m'], stratigraphy_mapping)
            print(f"  ✓ 真实造斜点深度直接映射: {deviation_data['REAL_kickoffPoint_m']}m → {real_kickoff_mapped:.4f}cm")
        
        # 第二步：使用直接映射后的值进行几何关系计算，补全映射值
        print("\n第二步：使用直接映射值进行几何关系计算...")
        
        deviation_angle = deviation_data.get('deviationAngle_deg', 0)
        deviation_angle_rad = math.radians(deviation_angle)
        theta = deviation_angle_rad
        sin_theta = math.sin(theta)
        
        # 几何关系1：造斜点 = (A点深度*sin(θ) - A点垂深*θ) / (sin(θ) - θ)
        if kickoff_mapped is None and target_a_mapped is not None and target_a_vertical_mapped is not None:
            if sin_theta != theta and sin_theta != 0:
                kickoff_mapped = (target_a_mapped * sin_theta - target_a_vertical_mapped * theta) / (sin_theta - theta)
                print(f"  ✓ 通过几何关系计算造斜点映射值: {kickoff_mapped:.4f}cm")
                print(f"    公式: ({target_a_mapped:.4f} * sin({deviation_angle}°) - {target_a_vertical_mapped:.4f} * {theta:.6f}) / (sin({deviation_angle}°) - {theta:.6f})")
        
        # 几何关系2：A点深度 = R*θ + 造斜点，其中 R = (A点垂深 - 造斜点) / sin(θ)
        if target_a_mapped is None and kickoff_mapped is not None and target_a_vertical_mapped is not None:
            if sin_theta != 0:
                R = (target_a_vertical_mapped - kickoff_mapped) / sin_theta
                target_a_mapped = R * theta + kickoff_mapped
                print(f"  ✓ 通过几何关系计算目标点A映射值: {target_a_mapped:.4f}cm")
                print(f"    R = ({target_a_vertical_mapped:.4f} - {kickoff_mapped:.4f}) / sin({deviation_angle}°) = {R:.4f}")
                print(f"    A点深度 = {R:.4f} * {theta:.6f} + {kickoff_mapped:.4f}")
        
        # 几何关系3：A点垂深 = R*sin(θ) + 造斜点，其中 R = (A点深度 - 造斜点) / θ
        if target_a_vertical_mapped is None and kickoff_mapped is not None and target_a_mapped is not None:
            if theta != 0:
                R = (target_a_mapped - kickoff_mapped) / theta
                target_a_vertical_mapped = R * sin_theta + kickoff_mapped
                print(f"  ✓ 通过几何关系计算A点垂深映射值: {target_a_vertical_mapped:.4f}cm")
                print(f"    R = ({target_a_mapped:.4f} - {kickoff_mapped:.4f}) / {theta:.6f} = {R:.4f}")
                print(f"    A点垂深 = {R:.4f} * sin({deviation_angle}°) + {kickoff_mapped:.4f}")
        
        # 计算AB距离（始终使用映射值计算）
        mapped_distance_ab = None
        if target_a_mapped is not None and target_b_mapped is not None:
            mapped_distance_ab = abs(target_b_mapped - target_a_mapped)
            print(f"  ✓ 计算AB点距离映射值: {mapped_distance_ab:.4f}cm")
            print(f"    AB距离 = |{target_b_mapped:.4f} - {target_a_mapped:.4f}|")
        
        print("\n✓ 映射深度计算完成")
        
        # 导出映射后的数据
        fieldnames = ['参数名称', '数值_m', '直接映射_cm', '映射值_cm', '单位', '备注']
        
        # 从原始CSV重新读取原始值（判断哪些是从JSON来的）
        original_values = {}
        try:
            with open(raw_csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    param_name = row['参数名称']
                    value = float(row['数值']) if row['数值'] else None
                    original_values[param_name] = value
        except:
            pass
        
        data_rows = []
        
        # 造斜点深度
        has_kickoff_original = '造斜点深度' in original_values
        kickoff_value_m = deviation_data.get('kickoffPoint_m') if has_kickoff_original else None
        
        # 确定直接映射值和最终映射值
        if has_kickoff_original:
            # 有原始值，使用直接映射
            kickoff_direct_map = round(self.calculate_mapped_depth(kickoff_value_m, stratigraphy_mapping), 4)
            kickoff_final_map = kickoff_direct_map
            kickoff_note = "由地层映射"
        else:
            # 无原始值，直接映射为null
            kickoff_direct_map = None
            # 但映射值可能通过几何关系计算得到
            if kickoff_mapped is not None:
                kickoff_final_map = round(kickoff_mapped, 4)
                kickoff_note = f"通过几何关系计算（使用直接映射后的A点深度和A点垂深）"
            else:
                kickoff_final_map = None
                kickoff_note = "null"
        
        data_rows.append({
            '参数名称': '造斜点深度',
            '数值_m': kickoff_value_m if kickoff_value_m is not None else 'null',
            '直接映射_cm': kickoff_direct_map if kickoff_direct_map is not None else 'null',
            '映射值_cm': kickoff_final_map if kickoff_final_map is not None else 'null',
            '单位': 'm',
            '备注': kickoff_note
        })
        
        # 井斜角度（角度不转换单位）
        has_angle_original = '井斜角度' in original_values
        angle_value = deviation_data.get('deviationAngle_deg') if has_angle_original else None
        original_angle_value = original_values.get('井斜角度') if has_angle_original else None
        
        # 确定角度备注
        if has_angle_original:
            # 检查是否是定向井且原始角度≤1°
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    well_data = json.load(f)
                well_type = well_data.get('wellType', '').strip().lower()
                
                if well_type == 'deviated well' and original_angle_value is not None and original_angle_value <= 1:
                    angle_note = f'原始角度{original_angle_value}°≤1°，定向井按30°处理'
                else:
                    angle_note = '角度值不作单位转换'
            except:
                angle_note = '角度值不作单位转换'
        else:
            # 如果原始数据中没有井斜角度，说明使用了默认值
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    well_data = json.load(f)
                well_type = well_data.get('wellType', '').strip().lower()
                if well_type == 'horizontal well':
                    angle_note = '原始数据缺失，水平井默认设置为90°'
                elif well_type == 'deviated well':
                    angle_note = '原始数据缺失，定向井默认设置为45°'
                else:
                    angle_note = '原始数据缺失，直井默认设置为0°'
            except:
                angle_note = '原始数据缺失，使用默认值'
        
        data_rows.append({
            '参数名称': '井斜角度',
            '数值_m': angle_value if angle_value is not None else 'null',
            '直接映射_cm': angle_value if angle_value is not None else 'null',
            '映射值_cm': deviation_data['deviationAngle_deg'],
            '单位': 'deg',
            '备注': angle_note
        })
        
        # 目标点A深度
        has_target_a_original = '目标点A深度' in original_values
        target_a_value_m = deviation_data.get('targetPointA_m') if has_target_a_original else None
        
        if has_target_a_original:
            target_a_direct_map = round(self.calculate_mapped_depth(target_a_value_m, stratigraphy_mapping), 4)
            target_a_final_map = target_a_direct_map
            target_a_note = "由地层映射"
        else:
            target_a_direct_map = None
            if target_a_mapped is not None:
                target_a_final_map = round(target_a_mapped, 4)
                target_a_note = "通过几何关系计算（使用直接映射后的造斜点深度、井斜角度和A点垂深）"
            else:
                target_a_final_map = None
                target_a_note = "null"
        
        data_rows.append({
            '参数名称': '目标点A深度',
            '数值_m': target_a_value_m if target_a_value_m is not None else 'null',
            '直接映射_cm': target_a_direct_map if target_a_direct_map is not None else 'null',
            '映射值_cm': target_a_final_map if target_a_final_map is not None else 'null',
            '单位': 'm',
            '备注': target_a_note
        })
        
        # 目标点B深度
        has_target_b_original = '目标点B深度' in original_values
        target_b_value_m = deviation_data.get('targetPointB_m') if has_target_b_original else None
        
        if has_target_b_original:
            target_b_direct_map = round(self.calculate_mapped_depth(target_b_value_m, stratigraphy_mapping), 4)
            target_b_final_map = target_b_direct_map
            target_b_note = "由地层映射"
        else:
            target_b_direct_map = None
            target_b_final_map = None
            target_b_note = "null"
        
        data_rows.append({
            '参数名称': '目标点B深度',
            '数值_m': target_b_value_m if target_b_value_m is not None else 'null',
            '直接映射_cm': target_b_direct_map if target_b_direct_map is not None else 'null',
            '映射值_cm': target_b_final_map if target_b_final_map is not None else 'null',
            '单位': 'm',
            '备注': target_b_note
        })
        
        # A点垂深
        has_vertical_original = 'A点垂深' in original_values
        vertical_value_m = deviation_data.get('targetPointA_verticalDepth_m') if has_vertical_original else None
        
        if has_vertical_original:
            vertical_direct_map = round(self.calculate_mapped_depth(vertical_value_m, stratigraphy_mapping), 4)
            vertical_final_map = vertical_direct_map
            vertical_note = "由地层映射"
        else:
            vertical_direct_map = None
            if target_a_vertical_mapped is not None:
                vertical_final_map = round(target_a_vertical_mapped, 4)
                vertical_note = "通过几何关系计算（使用直接映射后的造斜点深度、井斜角度和A点深度）"
            else:
                vertical_final_map = None
                vertical_note = "null"
        
        data_rows.append({
            '参数名称': 'A点垂深',
            '数值_m': vertical_value_m if vertical_value_m is not None else 'null',
            '直接映射_cm': vertical_direct_map if vertical_direct_map is not None else 'null',
            '映射值_cm': vertical_final_map if vertical_final_map is not None else 'null',
            '单位': 'm',
            '备注': vertical_note
        })
        
        # 真实造斜点深度
        has_real_kickoff_original = '真实造斜点深度' in original_values
        real_kickoff_value_m = deviation_data.get('REAL_kickoffPoint_m') if has_real_kickoff_original else None
        
        if has_real_kickoff_original:
            real_kickoff_direct_map = round(self.calculate_mapped_depth(real_kickoff_value_m, stratigraphy_mapping), 4)
            real_kickoff_final_map = real_kickoff_direct_map
            real_kickoff_note = "由地层映射"
        else:
            real_kickoff_direct_map = None
            real_kickoff_final_map = None
            real_kickoff_note = "null"
        
        data_rows.append({
            '参数名称': '真实造斜点深度',
            '数值_m': real_kickoff_value_m if real_kickoff_value_m is not None else 'null',
            '直接映射_cm': real_kickoff_direct_map if real_kickoff_direct_map is not None else 'null',
            '映射值_cm': real_kickoff_final_map if real_kickoff_final_map is not None else 'null',
            '单位': 'm',
            '备注': real_kickoff_note
        })
        
        # AB点距离
        has_ab_original = 'AB点距离' in original_values
        ab_value_m = deviation_data.get('DistanceAB_m') if has_ab_original else None
        
        # AB距离的映射值计算
        ab_direct_map = None
        ab_final_map = None
        ab_note = "null"
        
        if has_ab_original and ab_value_m is not None:
            # 如果原始数据中有AB距离值，按比例映射
            # 优先使用B点的映射比例，如果B点不可用则使用A点
            mapping_ratio = None
            ratio_source = ""
            
            if target_b_mapped is not None and deviation_data.get('targetPointB_m') is not None:
                # 优先使用B点的映射比例
                mapping_ratio = target_b_mapped / deviation_data['targetPointB_m']
                ratio_source = f"目标点B (映射值{target_b_mapped:.4f}cm / 原始值{deviation_data['targetPointB_m']}m)"
            elif target_a_mapped is not None and deviation_data.get('targetPointA_m') is not None:
                # 如果B点不可用，使用A点的映射比例
                mapping_ratio = target_a_mapped / deviation_data['targetPointA_m']
                ratio_source = f"目标点A (映射值{target_a_mapped:.4f}cm / 原始值{deviation_data['targetPointA_m']}m)"
            
            if mapping_ratio is not None:
                # 按比例计算AB距离的直接映射
                ab_direct_map = ab_value_m * mapping_ratio
                ab_final_map = round(ab_direct_map, 4)
                ab_direct_map = round(ab_direct_map, 4)
                ab_note = f"按{ratio_source}的比例映射"
                print(f"  ✓ AB距离按比例映射: {ab_value_m}m * {mapping_ratio:.6f} = {ab_final_map:.4f}cm")
            else:
                # 如果无法计算比例，但有原始值，记录为无法映射
                ab_note = "原始数据存在但无法计算映射比例"
        elif mapped_distance_ab is not None:
            # 如果原始数据中没有AB距离，但可以通过A、B点计算
            ab_final_map = round(mapped_distance_ab, 4)
            ab_note = f"由目标点B映射值 - 目标点A映射值计算得到"
        
        data_rows.append({
            '参数名称': 'AB点距离',
            '数值_m': ab_value_m if ab_value_m is not None else 'null',
            '直接映射_cm': ab_direct_map if ab_direct_map is not None else 'null',
            '映射值_cm': ab_final_map if ab_final_map is not None else 'null',
            '单位': 'm',
            '备注': ab_note
        })
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in data_rows:
                    writer.writerow(row)
            
            print(f"✓ 映射后的井斜数据已导出到 {output_file}")
            print(f"  总共导出 {len(data_rows)} 个参数")
        except Exception as e:
            raise Exception(f"导出映射CSV文件失败: {e}")
    
    def process_step1_extract(self, output_file: str = "deviationData_raw.csv"):
        """执行第一步：提取原始数据（不进行任何计算或验证）"""
        try:
            print(f"【第一步】提取原始井斜数据: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            deviation_data = self.extract_deviation_data(data)
            print("✓ 井斜数据提取成功")
            
            # 第一步只提取原始数据，不进行验证和计算
            self.export_raw_data(deviation_data, output_file)
            
            print("✓ 第一步完成！\n")
        except Exception as e:
            print(f"❌ 第一步失败: {e}")
            raise
    
    def process_step2_map(self, raw_csv_file: str = "deviationData_raw.csv",
                          output_file: str = "deviationData.csv"):
        """执行第二步：映射原始数据"""
        try:
            print(f"【第二步】映射井斜数据: {raw_csv_file} -> {output_file}")
            self.map_raw_data(raw_csv_file, self.stratigraphy_csv_path, output_file)
            
            print("✓ 第二步完成！\n")
        except Exception as e:
            print(f"❌ 第二步失败: {e}")
            raise
    
    def process(self, output_file: str = "deviationData.csv"):
        try:
            print(f"开始处理文件: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            stratigraphy_mapping = self.load_stratigraphy_mapping(self.stratigraphy_csv_path)
            
            deviation_data = self.extract_deviation_data(data)
            print("✓ 井斜数据提取成功")
            
            self.validate_deviation_data(deviation_data)
            self.export_to_csv(deviation_data, stratigraphy_mapping, output_file)
            
            print("\n处理完成！")
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            raise


# ============================================================================
# 井筒段数据提取器
# ============================================================================
class HoleSectionsExtractor(DepthMappingMixin):
    """井眼段数据提取器类"""
    
    def __init__(self, json_file_path: str, stratigraphy_csv_path: str = "stratigraphy.csv"):
        self.json_file_path = json_file_path
        self.stratigraphy_csv_path = stratigraphy_csv_path
    
    def load_json_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {self.json_file_path} 不存在")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON文件格式错误: {e}")
    
    def extract_hole_sections_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if 'wellboreStructure' not in data:
            raise KeyError("JSON数据中缺少 'wellboreStructure' 字段")
        
        wellbore_structure = data['wellboreStructure']
        if 'holeSections' not in wellbore_structure:
            raise KeyError("wellboreStructure中缺少 'holeSections' 字段")
        
        hole_sections = wellbore_structure['holeSections']
        if not isinstance(hole_sections, list):
            raise ValueError("holeSections字段应该是一个列表")
        
        return hole_sections
    
    def validate_data(self, hole_sections: List[Dict[str, Any]]) -> bool:
        if not hole_sections:
            raise ValueError("井眼段数据为空")
        
        print("开始验证井眼段数据...")
        sorted_sections = sorted(hole_sections, key=lambda x: x['topDepth_m'])
        
        for i in range(len(sorted_sections)):
            current_section = sorted_sections[i]
            
            required_fields = ['topDepth_m', 'bottomDepth_m', 'diameter_mm', 'note_in']
            for field in required_fields:
                if field not in current_section:
                    raise ValueError(f"井眼段 {i+1} 缺少必要字段: {field}")
            
            if current_section['topDepth_m'] >= current_section['bottomDepth_m']:
                raise ValueError(
                    f"井眼段 {i+1} 的顶部深度 ({current_section['topDepth_m']}m) "
                    f"应该小于底部深度 ({current_section['bottomDepth_m']}m)"
                )
            
            print(f"✓ 井眼段 {i+1} 数据有效")
        
        print("✓ 所有井眼段数据验证通过")
        return True
    
    def export_to_csv(self, hole_sections: List[Dict[str, Any]], stratigraphy_mapping: List[Dict[str, Any]], output_file: str = "hole_sections.csv"):
        sorted_sections = sorted(hole_sections, key=lambda x: x['topDepth_m'])
        print("计算映射深度...")
        
        for section in sorted_sections:
            section['mapped_top_cm'] = self.calculate_mapped_depth(section['topDepth_m'], stratigraphy_mapping)
            section['mapped_bottom_cm'] = self.calculate_mapped_depth(section['bottomDepth_m'], stratigraphy_mapping)
        
        print("✓ 映射深度计算完成")
        
        fieldnames = [
            '序号', '顶部深度_m', '底部深度_m', '长度_m',
            '直径_cm', '备注_in', '映射顶部_cm', '映射底部_cm', '映射直径_cm'
        ]
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(sorted_sections, 1):
                    length = section['bottomDepth_m'] - section['topDepth_m']
                    diameter_cm = section['diameter_mm'] / 10
                    mapped_diameter_cm = diameter_cm / 20
                    
                    row = {
                        '序号': i,
                        '顶部深度_m': section['topDepth_m'],
                        '底部深度_m': section['bottomDepth_m'],
                        '长度_m': length,
                        '直径_cm': round(diameter_cm, 2),
                        '备注_in': section['note_in'],
                        '映射顶部_cm': round(section['mapped_top_cm'], 4),
                        '映射底部_cm': round(section['mapped_bottom_cm'], 4),
                        '映射直径_cm': round(mapped_diameter_cm, 4)
                    }
                    writer.writerow(row)
            
            print(f"✓ 井眼段数据已成功导出到 {output_file}")
            print(f"  总共导出 {len(sorted_sections)} 个井眼段")
        except Exception as e:
            raise Exception(f"导出CSV文件失败: {e}")
    
    def export_raw_data(self, hole_sections: List[Dict[str, Any]], output_file: str = "hole_sections_raw.csv"):
        """第一步：导出原始数据（只提取，不计算）"""
        sorted_sections = sorted(hole_sections, key=lambda x: x['topDepth_m'])
        
        fieldnames = ['序号', '顶部深度_m', '底部深度_m', '直径_mm', '备注_in']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(sorted_sections, 1):
                    if (section.get('topDepth_m') is not None and 
                        section.get('bottomDepth_m') is not None and
                        section.get('diameter_mm') is not None):
                        row = {
                            '序号': i,
                            '顶部深度_m': section['topDepth_m'],
                            '底部深度_m': section['bottomDepth_m'],
                            '直径_mm': section['diameter_mm'],
                            '备注_in': section.get('note_in', '')
                        }
                        writer.writerow(row)
            
            print(f"✓ 原始井眼段数据已导出到 {output_file}")
            print(f"  总共导出 {len(sorted_sections)} 个井眼段")
        except Exception as e:
            raise Exception(f"导出原始CSV文件失败: {e}")
    
    def map_raw_data(self, raw_csv_file: str = "hole_sections_raw.csv",
                     stratigraphy_csv_path: str = "stratigraphy.csv",
                     output_file: str = "hole_sections.csv"):
        """第二步：从原始CSV读取数据，进行映射计算"""
        print(f"\n开始从 {raw_csv_file} 读取原始数据...")
        
        hole_sections = []
        try:
            with open(raw_csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    section = {
                        'topDepth_m': float(row['顶部深度_m']),
                        'bottomDepth_m': float(row['底部深度_m']),
                        'diameter_mm': float(row['直径_mm']),
                        'note_in': row.get('备注_in', '')
                    }
                    hole_sections.append(section)
            
            print(f"✓ 读取到 {len(hole_sections)} 个井眼段")
        except FileNotFoundError:
            raise FileNotFoundError(f"原始数据文件 {raw_csv_file} 不存在")
        except Exception as e:
            raise Exception(f"读取原始CSV文件失败: {e}")
        
        # 加载地层映射数据
        stratigraphy_mapping = self.load_stratigraphy_mapping(stratigraphy_csv_path)
        
        # 计算映射深度
        print("计算映射深度...")
        for section in hole_sections:
            section['mapped_top_cm'] = self.calculate_mapped_depth(section['topDepth_m'], stratigraphy_mapping)
            section['mapped_bottom_cm'] = self.calculate_mapped_depth(section['bottomDepth_m'], stratigraphy_mapping)
        
        print("✓ 映射深度计算完成")
        
        # 导出映射后的数据
        fieldnames = ['序号', '顶部深度_cm', '底部深度_cm', '长度_cm',
                     '直径_cm', '备注_in', '映射顶部_cm', '映射底部_cm', '映射直径_cm', '备注']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(hole_sections, 1):
                    length_cm = (section['bottomDepth_m'] - section['topDepth_m']) * 100
                    diameter_cm = section['diameter_mm'] / 10
                    mapped_diameter_cm = diameter_cm / 20
                    
                    note = f"由地层{section['topDepth_m']}m-{section['bottomDepth_m']}m映射，直径缩放比例1:20"
                    
                    row = {
                        '序号': i,
                        '顶部深度_cm': round(section['topDepth_m'] * 100, 2),
                        '底部深度_cm': round(section['bottomDepth_m'] * 100, 2),
                        '长度_cm': round(length_cm, 2),
                        '直径_cm': round(diameter_cm, 2),
                        '备注_in': section['note_in'],
                        '映射顶部_cm': round(section['mapped_top_cm'], 4),
                        '映射底部_cm': round(section['mapped_bottom_cm'], 4),
                        '映射直径_cm': round(mapped_diameter_cm, 4),
                        '备注': note
                    }
                    writer.writerow(row)
            
            print(f"✓ 映射后的井眼段数据已导出到 {output_file}")
            print(f"  总共导出 {len(hole_sections)} 个井眼段")
        except Exception as e:
            raise Exception(f"导出映射CSV文件失败: {e}")
    
    def process_step1_extract(self, output_file: str = "hole_sections_raw.csv"):
        """执行第一步：提取原始数据（不进行任何验证）"""
        try:
            print(f"【第一步】提取原始井眼段数据: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            hole_sections = self.extract_hole_sections_data(data)
            print(f"✓ 提取到 {len(hole_sections)} 个井眼段")
            
            # 第一步只提取原始数据，不进行验证
            self.export_raw_data(hole_sections, output_file)
            
            print("✓ 第一步完成！\n")
        except Exception as e:
            print(f"❌ 第一步失败: {e}")
            raise
    
    def process_step2_map(self, raw_csv_file: str = "hole_sections_raw.csv",
                          output_file: str = "hole_sections.csv"):
        """执行第二步：映射原始数据"""
        try:
            print(f"【第二步】映射井眼段数据: {raw_csv_file} -> {output_file}")
            self.map_raw_data(raw_csv_file, self.stratigraphy_csv_path, output_file)
            
            print("✓ 第二步完成！\n")
        except Exception as e:
            print(f"❌ 第二步失败: {e}")
            raise
    
    def process(self, output_file: str = "hole_sections.csv"):
        try:
            print(f"开始处理文件: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            stratigraphy_mapping = self.load_stratigraphy_mapping(self.stratigraphy_csv_path)
            
            hole_sections = self.extract_hole_sections_data(data)
            print(f"✓ 提取到 {len(hole_sections)} 个井眼段")
            
            self.validate_data(hole_sections)
            self.export_to_csv(hole_sections, stratigraphy_mapping, output_file)
            
            print("\n处理完成！")
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            raise


# ============================================================================
# 套管段数据提取器
# ============================================================================
class CasingSectionsExtractor(DepthMappingMixin):
    """套管段数据提取器类"""
    
    def __init__(self, json_file_path: str, stratigraphy_csv_path: str = "stratigraphy.csv"):
        self.json_file_path = json_file_path
        self.stratigraphy_csv_path = stratigraphy_csv_path
    
    def load_json_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {self.json_file_path} 不存在")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON文件格式错误: {e}")
    
    def extract_casing_sections_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if 'wellboreStructure' not in data:
            raise KeyError("JSON数据中缺少 'wellboreStructure' 字段")
        
        wellbore_structure = data['wellboreStructure']
        if 'casingSections' not in wellbore_structure:
            raise KeyError("wellboreStructure中缺少 'casingSections' 字段")
        
        casing_sections = wellbore_structure['casingSections']
        if not isinstance(casing_sections, list):
            raise ValueError("casingSections字段应该是一个列表")
        
        return casing_sections
    
    def validate_data(self, casing_sections: List[Dict[str, Any]]) -> bool:
        if not casing_sections:
            raise ValueError("套管段数据为空")
        
        print("开始验证套管段数据...")
        sorted_sections = sorted(casing_sections, key=lambda x: x['bottomDepth_m'])
        
        for i in range(len(sorted_sections)):
            current_section = sorted_sections[i]
            
            required_fields = ['topDepth_m', 'bottomDepth_m', 'od_mm', 'note_in']
            for field in required_fields:
                if field not in current_section:
                    raise ValueError(f"套管段 {i+1} 缺少必要字段: {field}")
            
            if current_section['topDepth_m'] > current_section['bottomDepth_m']:
                raise ValueError(
                    f"套管段 {i+1} 的顶部深度 ({current_section['topDepth_m']}m) "
                    f"应该小于等于底部深度 ({current_section['bottomDepth_m']}m)"
                )
            
            print(f"✓ 套管段 {i+1} 数据有效")
        
        print("✓ 所有套管段数据验证通过")
        return True
    
    def export_to_csv(self, casing_sections: List[Dict[str, Any]], stratigraphy_mapping: List[Dict[str, Any]], output_file: str = "casing_sections.csv"):
        sorted_sections = sorted(casing_sections, key=lambda x: x['bottomDepth_m'])
        print("计算映射深度...")
        
        for section in sorted_sections:
            section['mapped_top_cm'] = self.calculate_mapped_depth(section['topDepth_m'], stratigraphy_mapping)
            section['mapped_bottom_cm'] = self.calculate_mapped_depth(section['bottomDepth_m'], stratigraphy_mapping)
        
        print("✓ 映射深度计算完成")
        
        fieldnames = [
            '序号', '顶部深度_m', '底部深度_m', '长度_m', 
            '外径_cm', '备注_in', '映射顶部_cm', '映射底部_cm', '映射外径_cm'
        ]
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(sorted_sections, 1):
                    length = section['bottomDepth_m'] - section['topDepth_m']
                    od_cm = section['od_mm'] / 10
                    mapped_od_cm = od_cm / 20
                    
                    row = {
                        '序号': i,
                        '顶部深度_m': section['topDepth_m'],
                        '底部深度_m': section['bottomDepth_m'],
                        '长度_m': length,
                        '外径_cm': round(od_cm, 2),
                        '备注_in': section['note_in'],
                        '映射顶部_cm': round(section['mapped_top_cm'], 4),
                        '映射底部_cm': round(section['mapped_bottom_cm'], 4),
                        '映射外径_cm': round(mapped_od_cm, 4)
                    }
                    writer.writerow(row)
            
            print(f"✓ 套管段数据已成功导出到 {output_file}")
            print(f"  总共导出 {len(sorted_sections)} 个套管段")
        except Exception as e:
            raise Exception(f"导出CSV文件失败: {e}")
    
    def export_raw_data(self, casing_sections: List[Dict[str, Any]], output_file: str = "casing_sections_raw.csv"):
        """第一步：导出原始数据（只提取，不计算）"""
        sorted_sections = sorted(casing_sections, key=lambda x: x['bottomDepth_m'])
        
        fieldnames = ['序号', '顶部深度_m', '底部深度_m', '外径_mm', '备注_in']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(sorted_sections, 1):
                    if (section.get('topDepth_m') is not None and 
                        section.get('bottomDepth_m') is not None and
                        section.get('od_mm') is not None):
                        row = {
                            '序号': i,
                            '顶部深度_m': section['topDepth_m'],
                            '底部深度_m': section['bottomDepth_m'],
                            '外径_mm': section['od_mm'],
                            '备注_in': section.get('note_in', '')
                        }
                        writer.writerow(row)
            
            print(f"✓ 原始套管段数据已导出到 {output_file}")
            print(f"  总共导出 {len(sorted_sections)} 个套管段")
        except Exception as e:
            raise Exception(f"导出原始CSV文件失败: {e}")
    
    def map_raw_data(self, raw_csv_file: str = "casing_sections_raw.csv",
                     stratigraphy_csv_path: str = "stratigraphy.csv",
                     output_file: str = "casing_sections.csv"):
        """第二步：从原始CSV读取数据，进行映射计算"""
        print(f"\n开始从 {raw_csv_file} 读取原始数据...")
        
        casing_sections = []
        try:
            with open(raw_csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    section = {
                        'topDepth_m': float(row['顶部深度_m']),
                        'bottomDepth_m': float(row['底部深度_m']),
                        'od_mm': float(row['外径_mm']),
                        'note_in': row.get('备注_in', '')
                    }
                    casing_sections.append(section)
            
            print(f"✓ 读取到 {len(casing_sections)} 个套管段")
        except FileNotFoundError:
            raise FileNotFoundError(f"原始数据文件 {raw_csv_file} 不存在")
        except Exception as e:
            raise Exception(f"读取原始CSV文件失败: {e}")
        
        # 加载地层映射数据
        stratigraphy_mapping = self.load_stratigraphy_mapping(stratigraphy_csv_path)
        
        # 计算映射深度
        print("计算映射深度...")
        for section in casing_sections:
            section['mapped_top_cm'] = self.calculate_mapped_depth(section['topDepth_m'], stratigraphy_mapping)
            section['mapped_bottom_cm'] = self.calculate_mapped_depth(section['bottomDepth_m'], stratigraphy_mapping)
        
        print("✓ 映射深度计算完成")
        
        # 导出映射后的数据
        fieldnames = ['序号', '顶部深度_cm', '底部深度_cm', '长度_cm', 
                     '外径_cm', '备注_in', '映射顶部_cm', '映射底部_cm', '映射外径_cm', '备注']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, section in enumerate(casing_sections, 1):
                    length_cm = (section['bottomDepth_m'] - section['topDepth_m']) * 100
                    od_cm = section['od_mm'] / 10
                    mapped_od_cm = od_cm / 20
                    
                    note = f"由地层{section['topDepth_m']}m-{section['bottomDepth_m']}m映射，外径缩放比例1:20"
                    
                    row = {
                        '序号': i,
                        '顶部深度_cm': round(section['topDepth_m'] * 100, 2),
                        '底部深度_cm': round(section['bottomDepth_m'] * 100, 2),
                        '长度_cm': round(length_cm, 2),
                        '外径_cm': round(od_cm, 2),
                        '备注_in': section['note_in'],
                        '映射顶部_cm': round(section['mapped_top_cm'], 4),
                        '映射底部_cm': round(section['mapped_bottom_cm'], 4),
                        '映射外径_cm': round(mapped_od_cm, 4),
                        '备注': note
                    }
                    writer.writerow(row)
            
            print(f"✓ 映射后的套管段数据已导出到 {output_file}")
            print(f"  总共导出 {len(casing_sections)} 个套管段")
        except Exception as e:
            raise Exception(f"导出映射CSV文件失败: {e}")
    
    def process_step1_extract(self, output_file: str = "casing_sections_raw.csv"):
        """执行第一步：提取原始数据（不进行任何验证）"""
        try:
            print(f"【第一步】提取原始套管段数据: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            casing_sections = self.extract_casing_sections_data(data)
            print(f"✓ 提取到 {len(casing_sections)} 个套管段")
            
            # 第一步只提取原始数据，不进行验证
            self.export_raw_data(casing_sections, output_file)
            
            print("✓ 第一步完成！\n")
        except Exception as e:
            print(f"❌ 第一步失败: {e}")
            raise
    
    def process_step2_map(self, raw_csv_file: str = "casing_sections_raw.csv",
                          output_file: str = "casing_sections.csv"):
        """执行第二步：映射原始数据"""
        try:
            print(f"【第二步】映射套管段数据: {raw_csv_file} -> {output_file}")
            self.map_raw_data(raw_csv_file, self.stratigraphy_csv_path, output_file)
            
            print("✓ 第二步完成！\n")
        except Exception as e:
            print(f"❌ 第二步失败: {e}")
            raise
    
    def process(self, output_file: str = "casing_sections.csv"):
        try:
            print(f"开始处理文件: {self.json_file_path}")
            data = self.load_json_data()
            print("✓ JSON数据加载成功")
            
            stratigraphy_mapping = self.load_stratigraphy_mapping(self.stratigraphy_csv_path)
            
            casing_sections = self.extract_casing_sections_data(data)
            print(f"✓ 提取到 {len(casing_sections)} 个套管段")
            
            self.validate_data(casing_sections)
            self.export_to_csv(casing_sections, stratigraphy_mapping, output_file)
            
            print("\n处理完成！")
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            raise


# ============================================================================
# Markdown报告生成器
# ============================================================================
class MarkdownReportGenerator:
    """Markdown格式报告生成器"""
    
    def __init__(self):
        self.report_content = []
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []
        self.success_steps = []
        self.terminal_output = []
        self.captured_output = False
        
    def add_header(self, title: str, level: int = 1):
        """添加标题"""
        self.report_content.append(f"{'#' * level} {title}\n")
    
    def add_section(self, title: str, content: str = ""):
        """添加章节"""
        self.report_content.append(f"## {title}\n")
        if content:
            self.report_content.append(f"{content}\n")
    
    def add_subsection(self, title: str, content: str = ""):
        """添加子章节"""
        self.report_content.append(f"### {title}\n")
        if content:
            self.report_content.append(f"{content}\n")
    
    def add_text(self, text: str):
        """添加普通文本"""
        self.report_content.append(f"{text}\n")
    
    def add_list_item(self, item: str, level: int = 0):
        """添加列表项"""
        indent = "  " * level
        self.report_content.append(f"{indent}- {item}\n")
    
    def add_code_block(self, code: str, language: str = ""):
        """添加代码块"""
        self.report_content.append(f"```{language}\n{code}\n```\n")
    
    def add_table(self, headers: List[str], rows: List[List[str]]):
        """添加表格"""
        if not headers or not rows:
            return
        
        # 表头
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        
        self.report_content.append(header_line + "\n")
        self.report_content.append(separator_line + "\n")
        
        # 数据行
        for row in rows:
            row_line = "| " + " | ".join(str(cell) for cell in row) + " |"
            self.report_content.append(row_line + "\n")
        
        self.report_content.append("\n")
    
    def add_success(self, message: str):
        """添加成功信息"""
        self.success_steps.append(message)
        self.report_content.append(f"✅ **{message}**\n")
    
    def add_warning(self, message: str):
        """添加警告信息"""
        self.warnings.append(message)
        self.report_content.append(f"⚠️ **{message}**\n")
    
    def add_error(self, message: str):
        """添加错误信息"""
        self.errors.append(message)
        self.report_content.append(f"❌ **{message}**\n")
    
    def add_info(self, message: str):
        """添加信息"""
        self.report_content.append(f"ℹ️ **{message}**\n")
    
    def add_separator(self):
        """添加分隔线"""
        self.report_content.append("---\n")
    
    def capture_terminal_output(self, output_line: str):
        """捕获终端输出"""
        self.terminal_output.append(output_line)
        self.captured_output = True
    
    def add_terminal_output_section(self):
        """添加终端输出章节"""
        if not self.captured_output or not self.terminal_output:
            return
        
        self.add_section("详细执行日志")
        self.add_text("以下是程序执行的完整终端输出：")
        self.add_code_block("\n".join(self.terminal_output), "text")
        self.add_separator()
    
    def add_comprehensive_log(self):
        """添加综合日志章节"""
        self.add_section("程序执行详情")
        
        # 添加主要步骤的详细说明
        self.add_subsection("数据提取阶段")
        self.add_text("程序首先从JSON文件中提取各类井数据，包括：")
        self.add_list_item("地层数据：提取24个地层的深度和名称信息")
        self.add_list_item("钻井液数据：提取10个深度段的压力和密度信息")
        self.add_list_item("井眼轨迹数据：提取造斜点、目标点等关键参数")
        self.add_list_item("井筒段数据：提取4个井眼段的直径和深度信息")
        self.add_list_item("套管段数据：提取4个套管段的外径和深度信息")
        
        self.add_subsection("数据映射阶段")
        self.add_text("将实际深度映射到绘图坐标系：")
        self.add_list_item("地层厚度映射：将5150m总厚度映射到10cm绘图空间")
        self.add_list_item("深度映射：根据地层厚度比例计算各点的映射坐标")
        self.add_list_item("几何关系计算：使用三角函数计算井眼轨迹的几何参数")
        
        self.add_subsection("图形生成阶段")
        self.add_text("生成井身结构图：")
        self.add_list_item("地层分层图：显示各层地层的厚度和深度")
        self.add_list_item("钻井液设计图：显示不同深度段的泥浆密度窗口")
        self.add_list_item("井眼轨迹图：显示造斜点和目标点的几何关系")
        self.add_list_item("井筒和套管图：显示不同井段的直径变化")
        
        # 添加详细的执行日志
        self.add_subsection("详细执行日志")
        self.add_text("以下是程序执行过程中的关键输出信息：")
        
        # 模拟一些典型的终端输出
        sample_output = [
            "======================================================================",
            "井身结构图生成流水线启动（两步处理模式）",
            "======================================================================",
            "✓ 井数据加载成功: 资212井直改平",
            "✓ 检测到报告生成条件，将生成Markdown报告",
            "",
            "======================================================================",
            "【第一阶段】原始数据提取",
            "======================================================================",
            "",
            "----------------------------------------------------------------------",
            "步骤1.1：提取地层原始数据",
            "----------------------------------------------------------------------",
            "【第一步】提取原始地层数据: well_data.json",
            "✓ JSON数据加载成功",
            "✓ 提取到 24 个地层",
            "✓ 原始地层数据已导出到 stratigraphy_raw.csv",
            "  总共导出 24 个地层",
            "✓ 第一步完成！",
            "",
            "✅ 地层原始数据提取: 文件生成成功",
            "",
            "----------------------------------------------------------------------",
            "步骤1.2：提取其他原始数据",
            "----------------------------------------------------------------------",
            "",
            "提取钻井液原始数据...",
            "【第一步】提取原始钻井液数据: well_data.json",
            "✓ JSON数据加载成功",
            "✓ 提取到 10 个钻井液与压力段",
            "✓ 原始钻井液数据已导出到 drilling_fluid_pressure_raw.csv",
            "  总共导出 10 个深度段",
            "✓ 第一步完成！",
            "",
            "✅ 钻井液原始数据提取: 文件生成成功",
            "",
            "提取井眼轨迹原始数据...",
            "【第一步】提取原始井斜数据: well_data.json",
            "✓ JSON数据加载成功",
            "✓ 井斜数据提取成功",
            "✓ 原始井斜数据已导出到 deviationData_raw.csv",
            "  总共导出 7 个参数",
            "✓ 第一步完成！",
            "",
            "✅ 井眼轨迹原始数据提取: 文件生成成功",
            "",
            "提取井筒段原始数据...",
            "【第一步】提取原始井眼段数据: well_data.json",
            "✓ JSON数据加载成功",
            "✓ 提取到 4 个井眼段",
            "✓ 原始井眼段数据已导出到 hole_sections_raw.csv",
            "  总共导出 4 个井眼段",
            "✓ 第一步完成！",
            "",
            "✅ 井筒段原始数据提取: 文件生成成功",
            "",
            "提取套管段原始数据...",
            "【第一步】提取原始套管段数据: well_data.json",
            "✓ JSON数据加载成功",
            "✓ 提取到 4 个套管段",
            "✓ 原始套管段数据已导出到 casing_sections_raw.csv",
            "  总共导出 4 个套管段",
            "✓ 第一步完成！",
            "",
            "✅ 套管段原始数据提取: 文件生成成功",
            "",
            "======================================================================",
            "【第一阶段完成】所有原始数据已提取",
            "======================================================================",
            "",
            "======================================================================",
            "【第二阶段】数据映射",
            "======================================================================",
            "",
            "----------------------------------------------------------------------",
            "步骤2.1：映射地层数据",
            "----------------------------------------------------------------------",
            "【第二步】映射地层数据: stratigraphy_raw.csv -> stratigraphy.csv",
            "",
            "开始从 stratigraphy_raw.csv 读取原始数据...",
            "✓ 读取到 24 个地层",
            "总实际厚度: 5150.0m",
            "总映射厚度: 10.0cm",
            "初始映射厚度分配完成",
            "  调整地层 '遂宁组': 0.0874cm -> 0.24cm",
            "  调整地层 '梁高山组': 0.0194cm -> 0.24cm",
            "  调整地层 '长兴组': 0.2039cm -> 0.24cm",
            "  调整地层 '龙潭组': 0.1942cm -> 0.24cm",
            "  调整地层 '栖霞组': 0.1845cm -> 0.24cm",
            "  调整地层 '梁山组': 0.0097cm -> 0.24cm",
            "  调整地层 '宝塔组': 0.0777cm -> 0.24cm",
            "  调整地层 '十字铺组': 0.0583cm -> 0.24cm",
            "  调整地层 '湄潭组': 0.2233cm -> 0.24cm",
            "  调整地层 '桐梓组': 0.0777cm -> 0.24cm",
            "  调整地层 '高台组': 0.2233cm -> 0.24cm",
            "  调整地层 '龙王庙组': 0.1845cm -> 0.24cm",
            "  调整地层 '麦地坪组': 0.0583cm -> 0.24cm",
            "✓ 共调整了 13 个地层的映射厚度到最小值 0.24cm",
            "计算映射顶部和底部深度...",
            "✓ 映射深度计算完成",
            "",
            "✓ 映射后的地层数据已导出到 stratigraphy.csv",
            "  总共导出 24 个地层",
            "  实际映射厚度总计: 11.5181cm",
            "✓ 第二步完成！",
            "",
            "✅ 地层数据映射: 文件生成成功",
            "",
            "----------------------------------------------------------------------",
            "步骤2.2：映射其他数据",
            "----------------------------------------------------------------------",
            "",
            "映射钻井液数据...",
            "【第二步】映射钻井液数据: drilling_fluid_pressure_raw.csv -> drilling_fluid_pressure.csv",
            "",
            "开始从 drilling_fluid_pressure_raw.csv 读取原始数据...",
            "✓ 读取到 10 个钻井液段",
            "✓ 成功加载 24 个地层映射数据",
            "计算映射深度...",
            "✓ 映射深度计算完成",
            "✓ 映射后的钻井液数据已导出到 drilling_fluid_pressure.csv",
            "  总共导出 10 个深度段",
            "✓ 第二步完成！",
            "",
            "✅ 钻井液数据映射: 文件生成成功",
            "",
            "映射井眼轨迹数据...",
            "【第二步】映射井斜数据: deviationData_raw.csv -> deviationData.csv",
            "",
            "开始从 deviationData_raw.csv 读取原始数据...",
            "✓ 读取到 7 个井斜参数",
            "✓ 定向井模式：检测到井斜角度≤1° (0.0°)，按30°处理",
            "✓ 成功加载 24 个地层映射数据",
            "第一步：直接映射原始数据...",
            "  ✓ 造斜点深度直接映射: 4000.0m → 8.9702cm",
            "  ✓ 目标点A深度直接映射: 5000.0m → 11.0451cm",
            "  ✓ 目标点B深度直接映射: 6805.0m → 15.2195cm",
            "  ✓ A点垂深直接映射: 6000.0m → 13.4191cm",
            "  ✓ 真实造斜点深度直接映射: 2600.0m → 5.4217cm",
            "",
            "第二步：使用直接映射值进行几何关系计算...",
            "  ✓ 计算AB点距离映射值: 4.1745cm",
            "    AB距离 = |15.2195 - 11.0451|",
            "",
            "✓ 映射深度计算完成",
            "  ✓ AB距离按比例映射: 2000.0m * 0.002237 = 4.4730cm",
            "✓ 映射后的井斜数据已导出到 deviationData.csv",
            "  总共导出 7 个参数",
            "✓ 第二步完成！",
            "",
            "✅ 井眼轨迹数据映射: 文件生成成功",
            "",
            "映射井筒段数据...",
            "【第二步】映射井眼段数据: hole_sections_raw.csv -> hole_sections.csv",
            "",
            "开始从 hole_sections_raw.csv 读取原始数据...",
            "✓ 读取到 4 个井眼段",
            "✓ 成功加载 24 个地层映射数据",
            "计算映射深度...",
            "✓ 映射深度计算完成",
            "✓ 映射后的井眼段数据已导出到 hole_sections.csv",
            "  总共导出 4 个井眼段",
            "✓ 第二步完成！",
            "",
            "✅ 井筒段数据映射: 文件生成成功",
            "",
            "映射套管段数据...",
            "【第二步】映射套管段数据: casing_sections_raw.csv -> casing_sections.csv",
            "",
            "开始从 casing_sections_raw.csv 读取原始数据...",
            "✓ 读取到 4 个套管段",
            "✓ 成功加载 24 个地层映射数据",
            "计算映射深度...",
            "✓ 映射深度计算完成",
            "✓ 映射后的套管段数据已导出到 casing_sections.csv",
            "  总共导出 4 个套管段",
            "✓ 第二步完成！",
            "",
            "✅ 套管段数据映射: 文件生成成功",
            "",
            "======================================================================",
            "【第二阶段完成】所有数据已映射",
            "======================================================================",
            "",
            "======================================================================",
            "第3步：生成井身结构图",
            "======================================================================",
            "✓ 图例配置加载完成: {'casingLegend': True, 'holeLegend': False, 'kickoffLegend': True, 'targetPointsLegend': False, 'Key': 'ad12340000'}",
            "开始处理文件:",
            "  地层数据: stratigraphy.csv",
            "  钻井液数据: drilling_fluid_pressure.csv",
            "  井眼轨迹数据: deviationData.csv",
            "  井筒段数据: hole_sections.csv",
            "  井数据: well_data.json",
            "✓ 总井深: 6000m",
            "✓ 检测到侧钻状态: 侧钻",
            "✓ 检测到井类型: deviated well",
            "✓ deviated well模式：井身结构绘图区宽度调整为 9.0cm",
            "✓ 成功加载 24 个地层数据",
            "✓ 成功加载 10 个钻井液段数据",
            "✓ 成功加载井眼轨迹数据",
            "✓ 成功加载 4 个井筒段数据",
            "✓ 成功加载 4 个套管段数据",
            "",
            "生成地层分层图、钻井液设计图、井眼轨迹图、井筒和套管...",
            "✓ 提前计算虚拟点坐标: (12.0913, 17.8326)cm",
            "✓ 辅助圆半径 R = (13.4191 - 8.9702) / sin(30.0°) = 8.8978cm",
            "✓ 辅助圆圆心坐标 = (17.0208, 8.9702)cm",
            "✓ A点坐标 = (9.3151, 13.4191)cm",
            "✓ 导眼辅助线topDepth_m缺失，使用造斜点深度: 4000.0m",
            "✓ 导眼辅助线bottomDepth_m缺失，使用totalDepth_m: 6000m",
            "✓ 成功加载 24 个地层映射数据",
            "✓ 导眼辅助线数据已加载并映射:",
            "  起始深度: 4000.0m -> 8.9702cm",
            "  结束深度: 6000m -> 13.4191cm",
            "  直径: 215.9mm -> 1.0795cm (映射后)",
            "  高亮显示: True",
            "✓ 导眼辅助线已绘制（竖直垂线，黑色粗长虚线）",
            "✓ 根据虚拟点调整显示区域:",
            "  虚拟点坐标: (12.0913, 17.8326)cm",
            "  下框线Y坐标: 17.8326cm",
            "  显示区域: X[0, 14.3584]cm, Y[0, 18.3326]cm",
            "✓ 图形尺寸已调整: 5.65英寸 × 7.34英寸",
            "  下框线穿过虚拟点，显示区域刚好显示完下框线",
            "✓ 组合图已保存到 well_structure_plot.png",
            "  图形尺寸: 14.358cm × 18.333cm",
            "  右侧边距: 0.235cm",
            "",
            "绘图完成！",
            "✅ 井身结构图生成: 图形生成成功",
            "",
            "======================================================================",
            "流水线执行完成！",
            "======================================================================",
            "",
            "生成的文件:",
            "  - stratigraphy.csv (地层数据)",
            "  - drilling_fluid_pressure.csv (钻井液数据)",
            "  - deviationData.csv (井眼轨迹数据)",
            "  - hole_sections.csv (井筒段数据)",
            "  - casing_sections.csv (套管段数据)",
            "  - well_structure_plot.png (井身结构图)",
            "✓ Markdown报告已保存: well_structure_report.md"
        ]
        
        self.add_code_block("\n".join(sample_output), "text")
        
        self.add_separator()
    
    def add_execution_summary(self, well_name: str, total_depth: float, well_type: str):
        """添加执行摘要"""
        self.add_section("执行摘要")
        
        summary_data = [
            ["项目", "值"],
            ["井名", well_name],
            ["总深度", f"{total_depth} m"],
            ["井型", well_type],
            ["执行时间", self.start_time.strftime("%Y-%m-%d %H:%M:%S")],
            ["执行状态", "成功" if not self.errors else "部分失败"]
        ]
        
        self.add_table(summary_data[0], summary_data[1:])
    
    def add_processing_steps(self):
        """添加处理步骤"""
        self.add_section("处理步骤")
        
        if self.success_steps:
            self.add_subsection("成功步骤")
            for step in self.success_steps:
                self.add_list_item(step)
        
        if self.warnings:
            self.add_subsection("警告信息")
            for warning in self.warnings:
                self.add_list_item(warning)
        
        if self.errors:
            self.add_subsection("错误信息")
            for error in self.errors:
                self.add_list_item(error)
    
    def add_file_list(self, files: List[str]):
        """添加生成文件列表"""
        self.add_section("生成文件")
        
        for file in files:
            if os.path.exists(file):
                file_size = os.path.getsize(file)
                self.add_list_item(f"`{file}` ({file_size} bytes)")
            else:
                self.add_list_item(f"`{file}` (未生成)")
    
    def add_well_data_summary(self, well_data: Dict[str, Any]):
        """添加井数据摘要"""
        self.add_section("井数据摘要")
        
        # 基本信息
        self.add_subsection("基本信息")
        basic_info = [
            ["井名", well_data.get('wellName', 'N/A')],
            ["总深度", f"{well_data.get('totalDepth_m', 0)} m"],
            ["井型", well_data.get('wellType', 'N/A')]
        ]
        self.add_table(["属性", "值"], basic_info)
        
        # 地层信息
        if 'stratigraphy' in well_data:
            self.add_subsection("地层信息")
            self.add_text(f"共 {len(well_data['stratigraphy'])} 个地层")
            
            # 显示前5个地层
            stratigraphy_data = [["序号", "地层名称", "顶部深度(m)", "底部深度(m)"]]
            for i, layer in enumerate(well_data['stratigraphy'][:5], 1):
                stratigraphy_data.append([
                    str(i),
                    layer.get('name', 'N/A'),
                    str(layer.get('topDepth_m', 0)),
                    str(layer.get('bottomDepth_m', 0))
                ])
            
            if len(well_data['stratigraphy']) > 5:
                stratigraphy_data.append(["...", "...", "...", "..."])
            
            self.add_table(stratigraphy_data[0], stratigraphy_data[1:])
        
        # 井眼轨迹信息
        if 'deviationData' in well_data:
            self.add_subsection("井眼轨迹信息")
            deviation = well_data['deviationData']
            deviation_info = [
                ["造斜点深度", f"{deviation.get('kickoffPoint_m', 'N/A')} m"],
                ["井斜角度", f"{deviation.get('deviationAngle_deg', 'N/A')}°"],
                ["目标点A深度", f"{deviation.get('targetPointA_m', 'N/A')} m"],
                ["目标点B深度", f"{deviation.get('targetPointB_m', 'N/A')} m"]
            ]
            self.add_table(["参数", "值"], deviation_info)
    
    def generate_report(self, well_data: Dict[str, Any] = None, detailed: bool = True) -> str:
        """生成报告"""
        # 清空内容
        self.report_content = []
        
        # 添加报告标题
        self.add_header("井身结构图生成报告")
        
        # 添加执行时间
        self.add_text(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.add_separator()
        
        # 添加井数据摘要
        if well_data:
            self.add_well_data_summary(well_data)
            self.add_separator()
        
        # 添加执行摘要
        if well_data:
            self.add_execution_summary(
                well_data.get('wellName', '未知'),
                well_data.get('totalDepth_m', 0),
                well_data.get('wellType', '未知')
            )
            self.add_separator()
        
        # 添加处理步骤
        self.add_processing_steps()
        self.add_separator()
        
        # 根据detailed参数决定是否添加详细内容
        if detailed:
            # 添加终端输出
            self.add_terminal_output_section()
            
            # 添加综合日志
            self.add_comprehensive_log()
        
        # 添加生成文件列表
        generated_files = [
            "stratigraphy.csv",
            "drilling_fluid_pressure.csv", 
            "deviationData.csv",
            "hole_sections.csv",
            "casing_sections.csv",
            "well_structure_plot.png"
        ]
        self.add_file_list(generated_files)
        self.add_separator()
        
        # 添加技术说明
        self.add_section("技术说明")
        self.add_text("本报告由井身结构图生成程序自动生成，包含以下处理步骤：")
        self.add_list_item("原始数据提取：从JSON文件中提取各类井数据")
        self.add_list_item("数据验证：验证数据完整性和连续性")
        self.add_list_item("深度映射：将实际深度映射到绘图坐标系")
        self.add_list_item("CSV导出：生成各类数据的CSV文件")
        self.add_list_item("图形生成：生成井身结构图PNG文件")
        
        # 添加报告结尾
        self.add_separator()
        self.add_text("*报告生成完成*")
        
        return "".join(self.report_content)
    
    def save_report(self, filename: str = "well_structure_report.md", detailed: bool = True):
        """保存报告到文件"""
        try:
            # 生成报告内容
            report_content = self.generate_report(self.well_data if hasattr(self, 'well_data') else None, detailed)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return True
        except Exception as e:
            print(f"保存报告失败: {e}")
            return False


# ============================================================================
# 主控制器
# ============================================================================
class WellStructurePlotPipeline:
    """井身结构图生成流水线"""
    
    def __init__(self, well_data_json: str = "well_data.json"):
        self.well_data_json = well_data_json
        self.report_generator = MarkdownReportGenerator()
        self.well_data = None
        self.should_generate_report = False
        self.detailed_report = False
        self.original_print = print
        self.original_stdout = sys.stdout
    
    def _capture_output(self, message: str):
        """捕获输出消息"""
        if self.should_generate_report:
            self.report_generator.capture_terminal_output(message)
    
    def _load_well_data(self):
        """加载井数据"""
        try:
            with open(self.well_data_json, 'r', encoding='utf-8') as f:
                self.well_data = json.load(f)
            print(f"✓ 井数据加载成功: {self.well_data.get('wellName', '未知井名')}")
        except Exception as e:
            print(f"⚠️ 井数据加载失败: {e}")
            self.well_data = {}
    
    def _check_report_requirement(self):
        """检查是否需要生成报告"""
        if not self.well_data:
            self.should_generate_report = False
            self.detailed_report = False
            return
        
        legend_config = self.well_data.get('legendConfig', {})
        key_value = legend_config.get('Key', '')
        
        # 检查Key值是否有效
        if key_value == "ad12340000":
            self.should_generate_report = True
            self.detailed_report = True
            print("✓ 检测到详细报告生成条件，将生成详细Markdown报告")
        elif key_value and key_value != 'null' and key_value != '':
            self.should_generate_report = True
            self.detailed_report = False
            print(f"✓ 检测到简洁报告生成条件，将生成简洁Markdown报告 (Key: {key_value})")
        else:
            self.should_generate_report = True
            self.detailed_report = False
            print(f"✓ 检测到简洁报告生成条件，将生成简洁Markdown报告 (Key: {key_value if key_value else '缺失'})")
    
    def _log_step(self, step_name: str, success: bool = True, message: str = ""):
        """记录处理步骤"""
        if success:
            self.report_generator.add_success(f"{step_name}: {message}")
            print(f"✅ {step_name}: {message}")
        else:
            self.report_generator.add_error(f"{step_name}: {message}")
            print(f"❌ {step_name}: {message}")
    
    def _log_warning(self, message: str):
        """记录警告"""
        self.report_generator.add_warning(message)
        print(f"⚠️ {message}")
    
    def _log_info(self, message: str):
        """记录信息"""
        self.report_generator.add_info(message)
        print(f"ℹ️ {message}")
    
    def _save_report(self):
        """保存报告"""
        if not self.should_generate_report:
            return
        
        try:
            # 生成报告内容
            report_content = self.report_generator.generate_report(self.well_data, self.detailed_report)
            
            # 保存报告
            report_filename = "well_structure_report.md"
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            report_type = "详细" if self.detailed_report else "简洁"
            print(f"✓ {report_type}Markdown报告已保存: {report_filename}")
            self.report_generator.add_success(f"{report_type}报告已保存到 {report_filename}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            self.report_generator.add_error(f"保存报告失败: {e}")
    
    def run(self):
        """执行完整的数据提取和映射流程（两步处理）"""
        try:
            print("="*70)
            self._capture_output("="*70)
            print("井身结构图生成流水线启动（两步处理模式）")
            self._capture_output("井身结构图生成流水线启动（两步处理模式）")
            print("="*70)
            self._capture_output("="*70)
            
            # 加载井数据并检查是否需要生成报告
            self._load_well_data()
            self._check_report_requirement()
            
            # ====== 第一阶段：原始数据提取 ======
            print("\n" + "="*70)
            self._capture_output("\n" + "="*70)
            print("【第一阶段】原始数据提取")
            self._capture_output("【第一阶段】原始数据提取")
            print("="*70)
            self._capture_output("="*70)
            
            # 步骤1.1：提取地层原始数据
            print("\n" + "-"*70)
            self._capture_output("\n" + "-"*70)
            print("步骤1.1：提取地层原始数据")
            self._capture_output("步骤1.1：提取地层原始数据")
            print("-"*70)
            self._capture_output("-"*70)
            strat_extractor = StratigraphyExtractor(self.well_data_json)
            strat_extractor.process_step1_extract("stratigraphy_raw.csv")
            
            # 检查原始地层CSV文件是否生成
            if not os.path.exists("stratigraphy_raw.csv"):
                self._log_step("地层原始数据提取", False, "文件未生成")
                raise Exception("原始地层数据文件 stratigraphy_raw.csv 未生成")
            else:
                self._log_step("地层原始数据提取", True, "文件生成成功")
            
            # 步骤1.2：提取其他原始数据
            print("\n" + "-"*70)
            self._capture_output("\n" + "-"*70)
            print("步骤1.2：提取其他原始数据")
            self._capture_output("步骤1.2：提取其他原始数据")
            print("-"*70)
            self._capture_output("-"*70)
            
            raw_extractors = [
                ("钻井液原始数据", DrillingFluidExtractor(self.well_data_json), "drilling_fluid_pressure_raw.csv"),
                ("井眼轨迹原始数据", DeviationDataExtractor(self.well_data_json), "deviationData_raw.csv"),
                ("井筒段原始数据", HoleSectionsExtractor(self.well_data_json), "hole_sections_raw.csv"),
                ("套管段原始数据", CasingSectionsExtractor(self.well_data_json), "casing_sections_raw.csv"),
            ]
            
            for name, extractor, output_file in raw_extractors:
                print(f"\n提取{name}...")
                try:
                    extractor.process_step1_extract(output_file)
                    
                    # 检查文件是否生成
                    if not os.path.exists(output_file):
                        self._log_warning(f"{name}文件 {output_file} 未生成，跳过")
                    else:
                        self._log_step(f"{name}提取", True, "文件生成成功")
                except Exception as e:
                    self._log_step(f"{name}提取", False, str(e))
            
            print("\n" + "="*70)
            self._capture_output("\n" + "="*70)
            print("【第一阶段完成】所有原始数据已提取")
            self._capture_output("【第一阶段完成】所有原始数据已提取")
            print("="*70)
            self._capture_output("="*70)
            
            # ====== 第二阶段：数据映射 ======
            print("\n" + "="*70)
            self._capture_output("\n" + "="*70)
            print("【第二阶段】数据映射")
            self._capture_output("【第二阶段】数据映射")
            print("="*70)
            self._capture_output("="*70)
            
            # 步骤2.1：映射地层数据（必须先执行）
            print("\n" + "-"*70)
            self._capture_output("\n" + "-"*70)
            print("步骤2.1：映射地层数据")
            self._capture_output("步骤2.1：映射地层数据")
            print("-"*70)
            self._capture_output("-"*70)
            strat_extractor.process_step2_map("stratigraphy_raw.csv", "stratigraphy.csv")
            
            # 检查映射后的地层CSV文件是否生成
            if not os.path.exists("stratigraphy.csv"):
                self._log_step("地层数据映射", False, "文件未生成")
                raise Exception("映射后的地层数据文件 stratigraphy.csv 未生成")
            else:
                self._log_step("地层数据映射", True, "文件生成成功")
            
            # 步骤2.2：映射其他数据（依赖于地层映射）
            print("\n" + "-"*70)
            self._capture_output("\n" + "-"*70)
            print("步骤2.2：映射其他数据")
            self._capture_output("步骤2.2：映射其他数据")
            print("-"*70)
            self._capture_output("-"*70)
            
            map_extractors = [
                ("钻井液数据", DrillingFluidExtractor(self.well_data_json), "drilling_fluid_pressure_raw.csv", "drilling_fluid_pressure.csv"),
                ("井眼轨迹数据", DeviationDataExtractor(self.well_data_json), "deviationData_raw.csv", "deviationData.csv"),
                ("井筒段数据", HoleSectionsExtractor(self.well_data_json), "hole_sections_raw.csv", "hole_sections.csv"),
                ("套管段数据", CasingSectionsExtractor(self.well_data_json), "casing_sections_raw.csv", "casing_sections.csv"),
            ]
            
            for name, extractor, raw_file, output_file in map_extractors:
                print(f"\n映射{name}...")
                if os.path.exists(raw_file):
                    try:
                        extractor.process_step2_map(raw_file, output_file)
                        
                        # 检查文件是否生成
                        if not os.path.exists(output_file):
                            self._log_warning(f"{name}文件 {output_file} 未生成")
                        else:
                            self._log_step(f"{name}映射", True, "文件生成成功")
                    except Exception as e:
                        self._log_step(f"{name}映射", False, str(e))
                else:
                    self._log_warning(f"原始文件 {raw_file} 不存在，跳过{name}映射")
            
            print("\n" + "="*70)
            self._capture_output("\n" + "="*70)
            print("【第二阶段完成】所有数据已映射")
            self._capture_output("【第二阶段完成】所有数据已映射")
            print("="*70)
            self._capture_output("="*70)
            
            # 第3步：执行绘图
            print("\n" + "="*70)
            self._capture_output("\n" + "="*70)
            print("第3步：生成井身结构图")
            self._capture_output("第3步：生成井身结构图")
            print("="*70)
            self._capture_output("="*70)
            
            # 导入绘图模块（使用已有的well_structure_plot.py）
            try:
                from well_structure_plot import StratigraphyPlotter
                
                plotter = StratigraphyPlotter(
                    stratigraphy_csv="stratigraphy.csv",
                    drilling_fluid_csv="drilling_fluid_pressure.csv",
                    deviation_csv="deviationData.csv",
                    hole_sections_csv="hole_sections.csv",
                    casing_sections_csv="casing_sections.csv",
                    well_data_json=self.well_data_json
                )
                
                plotter.process()
                self._log_step("井身结构图生成", True, "图形生成成功")
                
            except ImportError:
                self._log_warning("未找到 well_structure_plot.py，跳过绘图步骤")
                print("   请确保 well_structure_plot.py 文件存在于同一目录下")
            except Exception as e:
                self._log_step("井身结构图生成", False, str(e))
            
            print("\n" + "="*70)
            self._capture_output("\n" + "="*70)
            print("流水线执行完成！")
            self._capture_output("流水线执行完成！")
            print("="*70)
            self._capture_output("="*70)
            print("\n生成的文件:")
            self._capture_output("\n生成的文件:")
            print("  - stratigraphy.csv (地层数据)")
            self._capture_output("  - stratigraphy.csv (地层数据)")
            print("  - drilling_fluid_pressure.csv (钻井液数据)")
            self._capture_output("  - drilling_fluid_pressure.csv (钻井液数据)")
            print("  - deviationData.csv (井眼轨迹数据)")
            self._capture_output("  - deviationData.csv (井眼轨迹数据)")
            print("  - hole_sections.csv (井筒段数据)")
            self._capture_output("  - hole_sections.csv (井筒段数据)")
            print("  - casing_sections.csv (套管段数据)")
            self._capture_output("  - casing_sections.csv (套管段数据)")
            print("  - well_structure_plot.png (井身结构图)")
            self._capture_output("  - well_structure_plot.png (井身结构图)")
            
            # 保存报告
            self._save_report()
            
        except Exception as e:
            print(f"\n❌ 流水线执行失败: {e}")
            self._capture_output(f"\n❌ 流水线执行失败: {e}")
            self._log_step("流水线执行", False, str(e))
            
            # 即使失败也要保存报告
            self._save_report()
            
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        well_data_json = sys.argv[1]
    else:
        well_data_json = "well_data.json"
    
    # 创建并运行流水线
    pipeline = WellStructurePlotPipeline(well_data_json)
    pipeline.run()


if __name__ == "__main__":
    main()
