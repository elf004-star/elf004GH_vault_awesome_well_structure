#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地层分层图形绘制程序
读取stratigraphy.csv数据，绘制地层分层图形
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
import numpy as np


class StratigraphyPlotter:
    """地层分层图形绘制器"""

    def __init__(self, stratigraphy_csv: str = "stratigraphy.csv", drilling_fluid_csv: str = "drilling_fluid_pressure.csv", deviation_csv: str = "deviationData.csv", hole_sections_csv: str = "hole_sections.csv", casing_sections_csv: str = "casing_sections.csv", well_data_json: str = "well_data.json"):
        """
        初始化绘制器

        Args:
            stratigraphy_csv: 地层CSV文件路径
            drilling_fluid_csv: 钻井液CSV文件路径
            deviation_csv: 井眼轨迹CSV文件路径
            hole_sections_csv: 井筒段CSV文件路径
            casing_sections_csv: 套管段CSV文件路径
            well_data_json: 井数据JSON文件路径
        """
        self.stratigraphy_csv = stratigraphy_csv
        self.drilling_fluid_csv = drilling_fluid_csv
        self.deviation_csv = deviation_csv
        self.hole_sections_csv = hole_sections_csv
        self.casing_sections_csv = casing_sections_csv
        self.well_data_json = well_data_json
        self.layer_width_cm = 2.123  # 地层方块宽度
        self.drilling_fluid_width_cm = 3.0  # 钻井液图宽度
        self.trajectory_width_cm = 6.0  # 井眼轨迹图宽度（井身结构绘图区）
        
        # 加载图例配置
        self.legend_config = self.load_legend_config()
        
        # 井类型和相关信息
        self.well_type = "straight well"  # 默认直井
        self.is_horizontal_well = False
        self.is_side_tracking = False  # 是否为侧钻
        self.well_data = {}  # 存储井数据
        self.total_depth_m = 0  # 总井深

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
    def load_well_data(self) -> dict:
        """
        加载井数据JSON文件
        
        Returns:
            井数据字典
        """
        try:
            import json
            with open(self.well_data_json, 'r', encoding='utf-8') as f:
                well_data = json.load(f)
            return well_data
        except Exception as e:
            print(f"⚠️ 读取井数据失败: {e}")
            return {}
    
    def load_legend_config(self):
        """
        加载图例配置
        
        Returns:
            图例配置字典，如果缺失则返回默认配置
        """
        try:
            well_data = self.load_well_data()
            legend_config = well_data.get('legendConfig', {})
            
            # 默认配置
            default_config = {
                'casingLegend': True,
                'holeLegend': True,
                'kickoffLegend': True,
                'targetPointsLegend': True
            }
            
            # 合并配置，缺失的项使用默认值
            for key, default_value in default_config.items():
                if key not in legend_config:
                    legend_config[key] = default_value
            
            print(f"✓ 图例配置加载完成: {legend_config}")
            return legend_config
            
        except Exception as e:
            print(f"⚠️ 加载图例配置失败，使用默认配置: {e}")
            # 返回默认配置
            return {
                'casingLegend': True,
                'holeLegend': True,
                'kickoffLegend': True,
                'targetPointsLegend': True
            }
    
    def detect_side_tracking_status(self):
        """
        检测侧钻状态
        基于 pilotHoleGuideLine 中的 side_tracking 字段
        """
        try:
            wellbore_structure = self.well_data.get('wellboreStructure', {})
            pilot_hole_data = wellbore_structure.get('pilotHoleGuideLine', None)
            
            if pilot_hole_data and isinstance(pilot_hole_data, dict):
                side_tracking = pilot_hole_data.get('side_tracking', False)
                self.is_side_tracking = bool(side_tracking)
                print(f"✓ 检测到侧钻状态: {'侧钻' if self.is_side_tracking else '造斜'}")
            else:
                # pilotHoleGuideLine 缺失或 side_tracking 缺失，默认为 false
                self.is_side_tracking = False
                print(f"✓ pilotHoleGuideLine 缺失或 side_tracking 缺失，默认侧钻状态: 造斜")
                
        except Exception as e:
            print(f"⚠️ 检测侧钻状态失败: {e}，默认侧钻状态: 造斜")
            self.is_side_tracking = False
    
    def detect_well_type(self, well_data: dict) -> str:
        """
        检测井类型并提取总井深
        
        Args:
            well_data: 井数据字典
            
        Returns:
            井类型字符串
        """
        # 存储井数据
        self.well_data = well_data
        
        # 提取总井深
        self.total_depth_m = well_data.get('totalDepth_m', 0)
        print(f"✓ 总井深: {self.total_depth_m}m")
        
        # 检测侧钻状态
        self.detect_side_tracking_status()
        
        well_type = well_data.get('wellType', '').strip().lower()
        
        # 如果wellType为空值或缺失，视为straight well
        if not well_type:
            return "straight well"
        
        # 验证井类型
        if well_type in ['horizontal well', 'deviated well']:
            # 检查deviationData是否存在且包含必要属性
            deviation_data = well_data.get('deviationData', {})
            
            # 处理kickoffPoint_m的备选值
            kickoff_point = deviation_data.get('kickoffPoint_m')
            if kickoff_point is None or kickoff_point == '' or str(kickoff_point).lower() == 'null':
                # 依次尝试备选值
                if 'REAL_kickoffPoint_m' in deviation_data:
                    kickoff_point = deviation_data['REAL_kickoffPoint_m']
                    print(f"✓ kickoffPoint_m为空，使用REAL_kickoffPoint_m: {kickoff_point}m")
                elif self.total_depth_m > 0:
                    kickoff_point = self.total_depth_m
                    print(f"✓ kickoffPoint_m为空，使用totalDepth_m: {kickoff_point}m")
                else:
                    kickoff_point = 0
                    print(f"✓ kickoffPoint_m为空，使用默认值0")
                
                # 更新deviationData中的值
                deviation_data['kickoffPoint_m'] = kickoff_point
            
            required_fields = ['kickoffPoint_m', 'deviationAngle_deg', 'targetPointA_m', 'targetPointB_m']
            
            missing_fields = [field for field in required_fields if field not in deviation_data]
            if missing_fields:
                print(f"❌ {well_type} 缺少必要的deviationData字段: {missing_fields}")
                return "straight well"
            
            return well_type
        elif well_type == 'straight well':
            # 直井时设置deviationData的默认值
            deviation_data = well_data.get('deviationData', {})
            deviation_data['deviationAngle_deg'] = 0
            deviation_data['kickoffPoint_m'] = self.total_depth_m
            deviation_data['targetPointA_m'] = self.total_depth_m
            deviation_data['targetPointA_verticalDepth_m'] = self.total_depth_m
            deviation_data['REAL_kickoffPoint_m'] = self.total_depth_m
            deviation_data['targetPointB_m'] = self.total_depth_m
            deviation_data['DistanceAB_m'] = 0
            
            print(f"✓ 直井模式：设置deviationData默认值")
            print(f"  井斜角度: 0度")
            print(f"  造斜点深度: {self.total_depth_m}m")
            print(f"  目标点A深度: {self.total_depth_m}m")
            print(f"  A点垂深: {self.total_depth_m}m")
            print(f"  真实造斜点深度: {self.total_depth_m}m")
            print(f"  目标点B深度: {self.total_depth_m}m")
            print(f"  AB点距离: 0m")
            
            return well_type
        else:
            print(f"⚠️ 未知的井类型: {well_type}，默认为straight well")
            return "straight well"
    
    def adjust_trajectory_width(self):
        """
        根据井类型调整井身结构绘图区宽度
        特殊规则：当deviated well的井斜角度≥89°时，按horizontal well处理
        """
        # 检查是否需要将deviated well当作horizontal well处理
        treat_as_horizontal = False
        if self.well_type == "deviated well":
            # 读取井斜角度
            try:
                deviation_df = pd.read_csv(self.deviation_csv, encoding='utf-8-sig')
                if not deviation_df.empty:
                    for _, row in deviation_df.iterrows():
                        if row['参数名称'] == '井斜角度':
                            # 使用映射值_cm列（这一列包含了默认值）
                            deviation_angle = float(row['映射值_cm']) if row['映射值_cm'] != 'null' else None
                            if deviation_angle is not None and deviation_angle >= 89:
                                treat_as_horizontal = True
                                print(f"✓ 检测到deviated well井斜角度≥89° ({deviation_angle}°)，按horizontal well处理")
                            break
            except Exception as e:
                print(f"⚠️ 读取井斜角度失败: {e}，按常规deviated well处理")
        
        if self.well_type == "horizontal well" or treat_as_horizontal:
            # horizontal well右侧区域扩大2倍
            self.trajectory_width_cm = 6.0 * 2  # 原宽度6.0，扩大2倍后为12.0
            self.is_horizontal_well = True
        elif self.well_type == "deviated well":
            # deviated well右侧区域扩大1倍
            self.trajectory_width_cm = 6.0 * 1.5  # 原宽度6.0，扩大1倍后为9.0
            self.is_horizontal_well = False
        else:
            # straight well保持原宽度
            self.trajectory_width_cm = 6.0
            self.is_horizontal_well = False
        
    def load_stratigraphy_data(self) -> pd.DataFrame:
        """
        加载地层数据

        Returns:
            地层数据DataFrame
        """
        try:
            df = pd.read_csv(self.stratigraphy_csv, encoding='utf-8-sig')
            print(f"✓ 成功加载 {len(df)} 个地层数据")
            return df
        except Exception as e:
            raise Exception(f"读取地层数据失败: {e}")

    def load_drilling_fluid_data(self) -> pd.DataFrame:
        """
        加载钻井液数据

        Returns:
            钻井液数据DataFrame
        """
        try:
            df = pd.read_csv(self.drilling_fluid_csv, encoding='utf-8-sig')
            print(f"✓ 成功加载 {len(df)} 个钻井液段数据")
            return df
        except Exception as e:
            raise Exception(f"读取钻井液数据失败: {e}")

    def load_deviation_data(self) -> pd.DataFrame:
        """
        加载井眼轨迹数据

        Returns:
            井眼轨迹数据DataFrame
        """
        # 如果是直井，跳过加载井眼轨迹数据
        if self.well_type == "straight well":
            print("✓ 直井模式：跳过井眼轨迹数据加载")
            return pd.DataFrame()  # 返回空DataFrame
        
        try:
            df = pd.read_csv(self.deviation_csv, encoding='utf-8-sig')
            print(f"✓ 成功加载井眼轨迹数据")
            return df
        except Exception as e:
            raise Exception(f"读取井眼轨迹数据失败: {e}")

    def load_hole_sections_data(self) -> pd.DataFrame:
        """
        加载井筒段数据

        Returns:
            井筒段数据DataFrame
        """
        try:
            df = pd.read_csv(self.hole_sections_csv, encoding='utf-8-sig')
            print(f"✓ 成功加载 {len(df)} 个井筒段数据")
            return df
        except Exception as e:
            raise Exception(f"读取井筒段数据失败: {e}")

    def load_casing_sections_data(self) -> pd.DataFrame:
        """
        加载套管段数据

        Returns:
            套管段数据DataFrame
        """
        try:
            df = pd.read_csv(self.casing_sections_csv, encoding='utf-8-sig')
            print(f"✓ 成功加载 {len(df)} 个套管段数据")
            return df
        except Exception as e:
            raise Exception(f"读取套管段数据失败: {e}")

    def get_layer_colors(self, num_layers: int) -> list:
        """
        生成地层颜色
        
        Args:
            num_layers: 地层数量
            
        Returns:
            颜色列表
        """
        # 定义一些地质常用颜色
        base_colors = [
            '#F5F5DC',  # 米色
            '#DEB887',  # 浅棕色
            '#D2B48C',  # 棕褐色
            '#BC8F8F',  # 玫瑰棕色
            '#F4A460',  # 沙棕色
            '#CD853F',  # 秘鲁色
            '#D2691E',  # 巧克力色
            '#A0522D',  # 马鞍棕色
            '#8B4513',  # 深棕色
            '#696969',  # 暗灰色
            '#778899',  # 浅石板灰
            '#708090',  # 石板灰
            '#2F4F4F',  # 深石板灰
            '#B0C4DE',  # 浅钢蓝色
            '#87CEEB',  # 天蓝色
            '#87CEFA',  # 浅天蓝色
            '#ADD8E6',  # 浅蓝色
            '#E0FFFF',  # 浅青色
            '#F0FFFF',  # 蔚蓝色
            '#F8F8FF',  # 幽灵白
        ]
        
        # 如果地层数量超过预定义颜色，使用渐变色
        if num_layers <= len(base_colors):
            return base_colors[:num_layers]
        else:
            # 生成渐变色
            colors = []
            for i in range(num_layers):
                hue = i / num_layers
                colors.append(plt.cm.Set3(hue))
            return colors
    
    def create_combined_plot(self, strat_df: pd.DataFrame, fluid_df: pd.DataFrame, deviation_df: pd.DataFrame, hole_sections_df: pd.DataFrame, casing_sections_df: pd.DataFrame, output_file: str = "well_structure_plot.png"):
        """
        创建地层分层图形、钻井液设计图和井眼轨迹图的组合

        Args:
            strat_df: 地层数据DataFrame
            fluid_df: 钻井液数据DataFrame
            deviation_df: 井眼轨迹数据DataFrame
            hole_sections_df: 井筒段数据DataFrame
            output_file: 输出文件名
        """
        # 按映射顶部深度排序
        strat_sorted = strat_df.sort_values('映射顶部_cm').reset_index(drop=True)
        fluid_sorted = fluid_df.sort_values('映射顶部_cm').reset_index(drop=True)

        # 提前计算虚拟点坐标（如果存在）
        virtual_point = None
        if self.well_type != "straight well" and not deviation_df.empty:
            # 从井眼轨迹数据中提取参数
            deviation_data = {}
            for _, row in deviation_df.iterrows():
                param_name = row['参数名称']
                if param_name == '造斜点深度':
                    deviation_data['kickoff_depth'] = row['映射值_cm']
                elif param_name == '井斜角度':
                    deviation_data['deviation_angle'] = row['映射值_cm']  # 使用映射值（包含默认值）
                elif param_name == '目标点A深度':
                    deviation_data['target_a_depth'] = row['映射值_cm']
                elif param_name == '目标点B深度':
                    deviation_data['target_b_depth'] = row['映射值_cm']
                elif param_name == 'AB点距离':
                    deviation_data['ab_distance'] = row['映射值_cm']
                elif param_name == 'A点垂深':
                    deviation_data['target_a_vertical_depth'] = row['映射值_cm']
            
            if all(key in deviation_data for key in ['kickoff_depth', 'deviation_angle', 'target_a_depth', 'target_b_depth', 'ab_distance']):
                # 计算B点坐标
                kickoff_depth = deviation_data['kickoff_depth']
                deviation_angle_deg = deviation_data['deviation_angle']
                if self.is_horizontal_well:
                    deviation_angle_deg = 90.0
                target_a_depth = deviation_data['target_a_depth']
                target_b_depth = deviation_data['target_b_depth']
                ab_distance = deviation_data['ab_distance']
                target_a_vertical_depth = deviation_data.get('target_a_vertical_depth')
                
                # 计算辅助圆参数
                deviation_angle_rad = np.radians(deviation_angle_deg)
                
                # 使用新方法计算半径：R = (A点垂深 - 造斜点深度) / sin(井斜角)
                if target_a_vertical_depth is not None and np.sin(deviation_angle_rad) != 0:
                    radius = (target_a_vertical_depth - kickoff_depth) / np.sin(deviation_angle_rad)
                else:
                    # 降级处理
                    radius = (target_a_depth - kickoff_depth) / 3.1415
                
                # 计算A点和B点坐标
                aux_x = self.layer_width_cm + self.drilling_fluid_width_cm + self.trajectory_width_cm / 3 + radius
                aux_y = kickoff_depth
                # 从造斜点开始，绕圆心逆时针旋转井斜角度到达A点
                a_x = aux_x + radius * np.cos(np.pi - deviation_angle_rad)
                a_y = aux_y + radius * np.sin(np.pi - deviation_angle_rad)
                b_x = a_x + ab_distance * np.sin(deviation_angle_rad)
                b_y = a_y + ab_distance * np.cos(deviation_angle_rad)
                
                # 计算虚拟点坐标
                min_wellbore_size = self.calculate_minimum_wellbore_size(hole_sections_df)
                # 使用最小井筒尺寸的一半
                half_min_wellbore_size = min_wellbore_size / 2
                virtual_x = b_x + half_min_wellbore_size
                virtual_y = b_y + half_min_wellbore_size
                virtual_point = {'x': virtual_x, 'y': virtual_y}
                
                print(f"✓ 提前计算虚拟点坐标: ({virtual_x:.4f}, {virtual_y:.4f})cm")

        # 计算图形尺寸 - 根据虚拟点调整
        total_height_cm = strat_sorted['映射底部_cm'].max()
        total_width_cm = self.layer_width_cm + self.drilling_fluid_width_cm + self.trajectory_width_cm
        
        # 如果有虚拟点，调整图形尺寸
        if virtual_point:
            # 下框线穿过虚拟点，显示区域刚好显示完下框线（多一点点）
            bottom_line_y = virtual_point['y']
            y_margin = 0.5  # 0.5cm的边距
            total_height_cm = max(total_height_cm, bottom_line_y + y_margin)
            
            # X方向也考虑虚拟点
            x_margin = max(1.0, virtual_point['x'] * 0.1)
            total_width_cm = max(total_width_cm, virtual_point['x'] + x_margin)
        
        # 在右侧增加1/20的范围
        extra_width_cm = total_width_cm / 60
        total_width_cm_with_margin = total_width_cm + extra_width_cm

        # 创建图形和轴，设置严格的1:1比例
        fig_width_inch = total_width_cm_with_margin / 2.54
        # 在下方增加当前高度的1/60
        fig_height_cm_extended = total_height_cm + total_height_cm / 60
        fig_height_inch = fig_height_cm_extended / 2.54
        fig, ax = plt.subplots(1, 1, figsize=(fig_width_inch, fig_height_inch))

        # 获取地层颜色
        strat_colors = self.get_layer_colors(len(strat_sorted))

        # 绘制地层方块
        for i, row in strat_sorted.iterrows():
            bottom = row['映射顶部_cm']
            height = row['映射厚度_cm']
            left = 0
            width = self.layer_width_cm

            rect = patches.Rectangle(
                (left, bottom), width, height,
                linewidth=1, edgecolor='black', facecolor=strat_colors[i],
                alpha=0.8
            )
            ax.add_patch(rect)

            # 添加地层名称
            text_x = left + width / 2
            text_y = bottom + height / 2

            if height > 0.5:
                fontsize = min(10, max(6, height * 2))
            else:
                fontsize = 6

            ax.text(text_x, text_y, row['地层名称'],
                   ha='center', va='center', fontsize=fontsize,
                   rotation=0, weight='bold')
            
            # 添加地层底部深度标注（左侧）
            depth_text_x = left - 0.1
            depth_text_y = bottom + height  # 地层底部位置
            actual_depth = row['底部深度_m']
            
            ax.text(depth_text_x, depth_text_y, f"{actual_depth}m",
                   ha='right', va='center', fontsize=7, color='black', weight='bold')

        # 绘制钻井液设计图
        self.draw_drilling_fluid_design(ax, fluid_sorted, total_height_cm)

        # 绘制井眼轨迹图和井筒
        trajectory_result = self.draw_trajectory_design(ax, deviation_df, hole_sections_df, casing_sections_df, total_height_cm, virtual_point)
        a_y = trajectory_result['a_y']
        kickoff_depth = trajectory_result['kickoff_depth']

        # 添加井筒和套管备注标注
        self.draw_hole_and_casing_notes(ax, hole_sections_df, casing_sections_df, total_height_cm, a_y, kickoff_depth)

        # 添加深度图例
        self.draw_depth_legend(ax, deviation_df, total_height_cm)

        # 设置坐标轴范围 - 下框线穿过虚拟点
        if virtual_point:
            # 如果有虚拟点，让下框线穿过虚拟点
            virtual_x = virtual_point['x']
            virtual_y = virtual_point['y']
            
            # 计算显示区域的边界
            # X方向：确保虚拟点在显示范围内，并留出适当边距
            x_margin = max(1.0, virtual_x * 0.1)  # 至少1cm边距，或虚拟点X坐标的10%
            x_max = max(total_width_cm_with_margin, virtual_x + x_margin)
            
            # Y方向：下框线要穿过虚拟点，显示区域刚好显示完下框线（多一点点）
            # 下框线的Y坐标就是虚拟点的Y坐标
            bottom_line_y = virtual_y
            # 显示区域的下边界稍微超出下框线一点点
            y_margin = 0.5  # 0.5cm的边距
            y_max = bottom_line_y + y_margin
            
            ax.set_xlim(0, x_max)
            # 在下方增加当前高度的1/60
            y_max_extended = y_max + y_max / 60
            ax.set_ylim(0, y_max_extended)
            
            print(f"✓ 根据虚拟点调整显示区域:")
            print(f"  虚拟点坐标: ({virtual_x:.4f}, {virtual_y:.4f})cm")
            print(f"  下框线Y坐标: {bottom_line_y:.4f}cm")
            print(f"  显示区域: X[0, {x_max:.4f}]cm, Y[0, {y_max:.4f}]cm")
        else:
            # 如果没有虚拟点，使用默认区域
            ax.set_xlim(0, total_width_cm_with_margin)
            # 在下方增加当前高度的1/60
            y_max_extended = total_height_cm + total_height_cm / 60
            ax.set_ylim(0, y_max_extended)
        
        ax.invert_yaxis()
        ax.set_aspect('equal', adjustable='box')
        
        # 如果有虚拟点，重新调整图形尺寸以适应新的显示区域
        if virtual_point:
            virtual_x = virtual_point['x']
            virtual_y = virtual_point['y']
            
            # 计算新的图形尺寸
            x_margin = max(1.0, virtual_x * 0.1)
            # Y方向：基于下框线穿过虚拟点的原则
            y_margin = 0.5  # 0.5cm的边距，刚好显示完下框线
            new_width_cm = max(total_width_cm_with_margin, virtual_x + x_margin)
            new_height_cm = virtual_y + y_margin  # 下框线Y坐标 + 边距
            # 在下方增加当前高度的1/60
            new_height_cm_extended = new_height_cm + new_height_cm / 60
            
            # 转换为英寸并调整图形尺寸
            new_fig_width_inch = new_width_cm / 2.54
            new_fig_height_inch = new_height_cm_extended / 2.54
            
            # 调整图形尺寸
            fig.set_size_inches(new_fig_width_inch, new_fig_height_inch)
            
            print(f"✓ 图形尺寸已调整: {new_fig_width_inch:.2f}英寸 × {new_fig_height_inch:.2f}英寸")
            print(f"  下框线穿过虚拟点，显示区域刚好显示完下框线")

        # 添加绘图区标注
        # 最左边绘图区标注地层
        stratigraphy_label_x = self.layer_width_cm / 2
        stratigraphy_label_y = -0.5
        ax.text(stratigraphy_label_x, stratigraphy_label_y, '地层', 
               ha='center', va='top', fontsize=12, weight='bold', color='black')
        
        # 最右边绘图区标注井身结构
        well_structure_label_x = self.layer_width_cm + self.drilling_fluid_width_cm + self.trajectory_width_cm / 2
        well_structure_label_y = -0.5
        ax.text(well_structure_label_x, well_structure_label_y, '井身结构', 
               ha='center', va='top', fontsize=12, weight='bold', color='black')

        # 去掉坐标轴
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        # 保存图形
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0,
                   facecolor='white', edgecolor='none')
        print(f"✓ 组合图已保存到 {output_file}")
        print(f"  图形尺寸: {total_width_cm_with_margin:.3f}cm × {total_height_cm:.3f}cm")
        print(f"  右侧边距: {extra_width_cm:.3f}cm")

        plt.show()

    def draw_drilling_fluid_design(self, ax, fluid_df: pd.DataFrame, total_height_cm: float):
        """
        绘制钻井液设计图

        Args:
            ax: matplotlib轴对象
            fluid_df: 钻井液数据DataFrame
            total_height_cm: 总高度
        """
        # 钻井液图的起始X位置
        fluid_start_x = self.layer_width_cm

        # 绘制背景框
        bg_rect = patches.Rectangle(
            (fluid_start_x, 0), self.drilling_fluid_width_cm, total_height_cm,
            linewidth=1, edgecolor='black', facecolor='white', alpha=1.0
        )
        ax.add_patch(bg_rect)

        # 绘制顶部刻度（每0.3标一次）
        scale_y = -0.3  # 刻度位置
        scale_values = [1.0, 1.3, 1.6, 1.9, 2.2]  # 间隔0.3
        scale_width = self.drilling_fluid_width_cm

        for val in scale_values:
            # 计算X位置（基于密度值）
            x_pos = fluid_start_x + ((val - 1.0) / 1.2) * scale_width
            ax.text(x_pos, scale_y, f"{val}", ha='center', va='top', fontsize=8)
            # 绘制刻度线
            ax.plot([x_pos, x_pos], [0, -0.1], 'k-', linewidth=0.5)

        # 绘制钻井液密度曲线
        for _, row in fluid_df.iterrows():
            top_depth = row['映射顶部_cm']
            bottom_depth = row['映射底部_cm']
            pore_pressure = row['孔隙压力_gcm3']
            min_density = row['泥浆密度窗口最小值_gcm3']
            max_density = row['泥浆密度窗口最大值_gcm3']

            # 计算X位置（基于密度值）
            def density_to_x(density):
                # 将密度值映射到X坐标
                return fluid_start_x + ((density - 1.0) / 1.2) * scale_width

            pore_x = density_to_x(pore_pressure)
            min_x = density_to_x(min_density)
            max_x = density_to_x(max_density)

            # 绘制孔隙压力线（红色）
            ax.plot([pore_x, pore_x], [top_depth, bottom_depth], 'r-', linewidth=2)

            # 绘制泥浆密度窗口（蓝色阴影区域）
            window_rect = patches.Rectangle(
                (min_x, top_depth), max_x - min_x, bottom_depth - top_depth,
                linewidth=0, facecolor='lightblue', alpha=0.3
            )
            ax.add_patch(window_rect)

            # 绘制窗口边界线（浅蓝色）
            ax.plot([min_x, min_x], [top_depth, bottom_depth], color='lightblue', linewidth=1)
            ax.plot([max_x, max_x], [top_depth, bottom_depth], color='lightblue', linewidth=1)

            # 添加数值标签
            mid_y = (top_depth + bottom_depth) / 2

            # 孔隙压力标签（红色）
            ax.text(pore_x - 0.1, mid_y, f"{pore_pressure}",
                   ha='right', va='center', fontsize=8, color='red', weight='bold')

            # 密度窗口标签（黑色）- 从最小值线位置开始
            ax.text(min_x, mid_y, f"{min_density}-{max_density}",
                   ha='left', va='center', fontsize=8, color='black')

    def draw_trajectory_design(self, ax, deviation_df: pd.DataFrame, hole_sections_df: pd.DataFrame, casing_sections_df: pd.DataFrame, total_height_cm: float, virtual_point: dict = None):
        """
        绘制井眼轨迹图和井筒

        Args:
            ax: matplotlib轴对象
            deviation_df: 井眼轨迹数据DataFrame
            hole_sections_df: 井筒段数据DataFrame
            total_height_cm: 总高度
        """
        # 井眼轨迹图的起始X位置
        trajectory_start_x = self.layer_width_cm + self.drilling_fluid_width_cm

        # 绘制背景框
        bg_rect = patches.Rectangle(
            (trajectory_start_x, 0), self.trajectory_width_cm, total_height_cm,
            linewidth=1, edgecolor='black', facecolor='white', alpha=1.0
        )
        ax.add_patch(bg_rect)

        # 设置原点位置
        if self.is_horizontal_well:
            # horizontal well：中轴线起始位置位于区域左侧1/3位置
            origin_x = trajectory_start_x + self.trajectory_width_cm / 3
        elif self.well_type == "deviated well":
            # deviated well：中轴线起始位置位于区域左侧1/3位置
            origin_x = trajectory_start_x + self.trajectory_width_cm / 3
        else:
            # straight well：中轴线位于绘图框上端的中点
            origin_x = trajectory_start_x + self.trajectory_width_cm / 2
        origin_y = 0

        # 从井眼轨迹数据中提取参数
        deviation_data = {}
        
        # 如果是直井，使用总井深作为造斜点，不绘制造斜点以下的内容
        if self.well_type == "straight well":
            # 计算总井深的映射深度
            # 使用main.py中的DeviationDataExtractor类
            # 由于main.py已经包含了所有提取器，这里需要重新导入
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from main import DeviationDataExtractor
            extractor = DeviationDataExtractor(self.well_data_json)
            stratigraphy_mapping = extractor.load_stratigraphy_mapping("stratigraphy.csv")
            kickoff_depth_mapped = extractor.calculate_mapped_depth(self.total_depth_m, stratigraphy_mapping)
            
            deviation_data = {
                'kickoff_depth': kickoff_depth_mapped,
                'deviation_angle': 0,
                'target_a_depth': kickoff_depth_mapped,
                'target_b_depth': kickoff_depth_mapped,
                'ab_distance': 0
            }
            print(f"✓ 直井模式：造斜点设置为总井深 {self.total_depth_m}m (映射深度: {kickoff_depth_mapped:.4f}cm)")
        else:
            # 非直井，从CSV数据中提取参数
            for _, row in deviation_df.iterrows():
                param_name = row['参数名称']
                if param_name == '造斜点深度':
                    deviation_data['kickoff_depth'] = row['映射值_cm']
                elif param_name == '井斜角度':
                    deviation_data['deviation_angle'] = row['映射值_cm']  # 使用映射值（包含默认值）
                elif param_name == '目标点A深度':
                    deviation_data['target_a_depth'] = row['映射值_cm']
                elif param_name == '目标点B深度':
                    deviation_data['target_b_depth'] = row['映射值_cm']
                elif param_name == 'AB点距离':
                    deviation_data['ab_distance'] = row['映射值_cm']
                elif param_name == 'A点垂深':
                    deviation_data['target_a_vertical_depth'] = row['映射值_cm']  # 添加A点垂深
                elif param_name == '真实造斜点深度':
                    deviation_data['real_kickoff_depth'] = row['映射值_cm']
                    deviation_data['real_kickoff_depth_actual'] = row['数值_m']  # 实际深度（m）

            # 检查是否有必要的数据
            if not all(key in deviation_data for key in ['kickoff_depth', 'deviation_angle', 'target_a_depth', 'target_b_depth', 'ab_distance']):
                print("❌ 井眼轨迹数据不完整")
                return

        # 提取数据
        kickoff_depth = deviation_data['kickoff_depth']
        deviation_angle_deg = deviation_data['deviation_angle']
        if self.is_horizontal_well:
            deviation_angle_deg = 90.0
        target_a_depth = deviation_data['target_a_depth']
        target_b_depth = deviation_data['target_b_depth']
        ab_distance = deviation_data['ab_distance']
        target_a_vertical_depth = deviation_data.get('target_a_vertical_depth')  # 获取A点垂深（可能为None）

        # 转换角度为弧度
        deviation_angle_rad = np.radians(deviation_angle_deg)

        # 1. 绘制从原点到造斜点的红色虚线
        ax.plot([origin_x, origin_x], [origin_y, kickoff_depth],
               'r--', linewidth=2, label='井眼轨迹')

        # 如果是直井，只绘制到造斜点（总井深），不绘制造斜点以下的内容
        if self.well_type == "straight well":
            # 直井不显示造斜点标记和标注
            # 直井不绘制造斜点以下的内容，设置虚拟值用于后续井筒绘制
            a_x = origin_x
            a_y = kickoff_depth
            b_x = origin_x
            b_y = kickoff_depth
            extend_x = origin_x
            extend_y = kickoff_depth
            aux_x = origin_x
            aux_y = kickoff_depth
            radius = 0
        else:
            # 非直井，绘制完整的井眼轨迹
            # 1. 确定辅助圆的半径：R = (A点垂深 - 造斜点深度) / sin(井斜角)
            if target_a_vertical_depth is not None and np.sin(deviation_angle_rad) != 0:
                radius = (target_a_vertical_depth - kickoff_depth) / np.sin(deviation_angle_rad)
                print(f"✓ 辅助圆半径 R = ({target_a_vertical_depth:.4f} - {kickoff_depth:.4f}) / sin({deviation_angle_deg}°) = {radius:.4f}cm")
            else:
                # 降级处理：如果没有A点垂深，使用原来的方法
                radius = (target_a_depth - kickoff_depth) / 3.1415
                print(f"⚠️  未找到A点垂深，使用降级方法计算半径: {radius:.4f}cm")
            
            # 2. 确定辅助圆的圆心位置：圆心在造斜点右边，坐标为(造斜点横坐标+R, 造斜点深度)
            aux_x = origin_x + radius
            aux_y = kickoff_depth
            print(f"✓ 辅助圆圆心坐标 = ({aux_x:.4f}, {aux_y:.4f})cm")
            
            # 3. 确定A点的位置：从造斜点开始，绕圆心逆时针旋转井斜角度
            # 造斜点相对于圆心的角度是180°（π），逆时针旋转井斜角度后，A点相对于圆心的角度是(π - 井斜角度)
            a_x = aux_x + radius * np.cos(np.pi - deviation_angle_rad)  # = aux_x - radius * cos(井斜角)
            a_y = aux_y + radius * np.sin(np.pi - deviation_angle_rad)  # = aux_y + radius * sin(井斜角)
            print(f"✓ A点坐标 = ({a_x:.4f}, {a_y:.4f})cm")
            
            # 4. 确定B点位置：B点坐标应该在A点坐标的右方
            # B横坐标=A横坐标+AB距离*sin(井斜角)，B纵坐标=A纵坐标+AB距离*cos(井斜角)
            b_x = a_x + ab_distance * np.sin(deviation_angle_rad)
            b_y = a_y + ab_distance * np.cos(deviation_angle_rad)

            # 5. 绘制造斜段圆弧（用多段虚线模拟）
            # 计算圆弧上的多个点来绘制虚线
            num_points = 20
            angles = np.linspace(np.pi, np.pi - deviation_angle_rad, num_points)
            arc_x = aux_x + radius * np.cos(angles)
            arc_y = aux_y + radius * np.sin(angles)

            # 绘制圆弧虚线
            ax.plot(arc_x, arc_y, 'r--', linewidth=2)

            # 6. 绘制从A点到B点的红色虚线
            ax.plot([a_x, b_x], [a_y, b_y], 'r--', linewidth=2)

            # 7. 井眼轨迹线要连接AB两点，并穿过B点（穿过长度为AB距离的1/10）
            extend_length = ab_distance / 10
            extend_x = b_x + extend_length * np.sin(deviation_angle_rad)
            extend_y = b_y + extend_length * np.cos(deviation_angle_rad)

            # 绘制B点后的延长虚线
            ax.plot([b_x, extend_x], [b_y, extend_y], 'r--', linewidth=2)

            # 6. 标记各个点
            # A点（红色）
            ax.plot(a_x, a_y, 'ro', markersize=6)
            ax.text(a_x + 0.1, a_y, 'A',
                   ha='left', va='center', fontsize=8, color='black', weight='bold')

            # B点（红色）
            ax.plot(b_x, b_y, 'ro', markersize=6)
            ax.text(b_x + 0.1, b_y, 'B',
                   ha='left', va='center', fontsize=8, color='black', weight='bold')
            
            # 真实造斜点（水平井为橘黄色，其他为蓝色）- 如果存在
            if 'real_kickoff_depth' in deviation_data:
                real_kickoff_depth = deviation_data['real_kickoff_depth']
                
                # 真实造斜点的横坐标与中轴线一致（造斜点以上）
                real_kickoff_x = origin_x
                
                # 根据侧钻状态选择颜色
                if self.is_side_tracking:
                    # 侧钻：橘黄色圆点 + 黑色×叉
                    ax.plot(real_kickoff_x, real_kickoff_depth, 'o', color='orange', markersize=4)
                    ax.plot(real_kickoff_x, real_kickoff_depth, 'x', color='black', markersize=6, markeredgewidth=1)
                else:
                    # 造斜：蓝色
                    ax.plot(real_kickoff_x, real_kickoff_depth, 'bo', markersize=4)

        # 7. 绘制井筒
        self.draw_wellbore(ax, hole_sections_df, origin_x, origin_y, kickoff_depth,
                          aux_x, aux_y, radius, deviation_angle_rad,
                          a_x, a_y, b_x, b_y, extend_x, extend_y)

        # 绘制套管
        self.draw_casing(ax, casing_sections_df, origin_x, origin_y, kickoff_depth,
                        aux_x, aux_y, radius, deviation_angle_rad,
                        a_x, a_y, b_x, b_y, extend_x, extend_y)
        
        # 虚拟点仅用于坐标计算，不进行绘制
        
        return {'a_y': a_y, 'kickoff_depth': kickoff_depth, 'virtual_point': virtual_point}

    def calculate_minimum_wellbore_size(self, hole_sections_df: pd.DataFrame) -> float:
        """
        计算所有井筒映射后的最小尺寸
        
        Args:
            hole_sections_df: 井筒段数据DataFrame
            
        Returns:
            最小尺寸（cm）
        """
        if hole_sections_df.empty:
            return 0.0
        
        # 计算所有井筒段的最小直径
        min_size = float('inf')
        
        for _, row in hole_sections_df.iterrows():
            diameter = float(row['映射直径_cm'])
            if diameter < min_size:
                min_size = diameter
        
        if min_size == float('inf'):
            return 0.0
        else:
            return min_size


    def load_and_map_pilot_hole_guide_line(self) -> dict:
        """
        加载并映射导眼辅助线数据
        
        Returns:
            包含映射后数据的字典，如果不需要绘制则返回None
        """
        # 只在水平井或定向井时处理
        if self.well_type not in ["horizontal well", "deviated well"]:
            return None
        
        # 检查pilotHoleGuideLine是否存在
        wellbore_structure = self.well_data.get('wellboreStructure', {})
        pilot_hole_data = wellbore_structure.get('pilotHoleGuideLine', None)
        
        if not pilot_hole_data:
            print("✓ 未找到导眼辅助线数据，跳过绘制")
            return None
        
        # 检查display标志
        if not pilot_hole_data.get('display', False):
            print("✓ 导眼辅助线display为false，跳过绘制")
            return None
        
        # 提取数据
        top_depth_m = pilot_hole_data.get('topDepth_m')
        bottom_depth_m = pilot_hole_data.get('bottomDepth_m')
        diameter_mm = pilot_hole_data.get('diameter_mm')
        
        # 检查diameter_mm是否存在（必要字段）
        if diameter_mm is None:
            print("⚠️ 导眼辅助线diameter_mm缺失，跳过绘制")
            return None
        
        # 处理topDepth_m缺失的情况：使用造斜点深度的映射值
        use_kickoff_mapped = False
        kickoff_mapped_cm = None
        if top_depth_m is None:
            try:
                import pandas as pd
                deviation_df = pd.read_csv(self.deviation_csv, encoding='utf-8-sig')
                for _, row in deviation_df.iterrows():
                    if row['参数名称'] == '造斜点深度':
                        kickoff_mapped_cm = row['映射值_cm']
                        if kickoff_mapped_cm != 'null' and kickoff_mapped_cm is not None:
                            kickoff_mapped_cm = float(kickoff_mapped_cm)
                            # 读取原始值用于显示
                            kickoff_value_m = row['数值_m']
                            if kickoff_value_m != 'null' and kickoff_value_m is not None:
                                top_depth_m = float(kickoff_value_m)
                                print(f"✓ 导眼辅助线topDepth_m缺失，使用造斜点深度: {top_depth_m}m")
                            else:
                                print(f"✓ 导眼辅助线topDepth_m缺失，使用造斜点映射值: {kickoff_mapped_cm}cm")
                                use_kickoff_mapped = True
                                top_depth_m = 0  # 占位符，实际使用映射值
                        break
                if kickoff_mapped_cm is None:
                    print("⚠️ 导眼辅助线topDepth_m缺失且无法从造斜点获取，跳过绘制")
                    return None
            except Exception as e:
                print(f"⚠️ 读取造斜点深度失败: {e}，跳过导眼辅助线绘制")
                return None
        
        # 处理bottomDepth_m缺失的情况
        if bottom_depth_m is None:
            # 优先使用totalDepth_m
            if self.total_depth_m is not None and self.total_depth_m > 0:
                bottom_depth_m = self.total_depth_m
                print(f"✓ 导眼辅助线bottomDepth_m缺失，使用totalDepth_m: {bottom_depth_m}m")
            else:
                # totalDepth_m也缺失，使用地层数据中最大的bottomDepth_m
                try:
                    import pandas as pd
                    strat_df = pd.read_csv(self.stratigraphy_csv, encoding='utf-8-sig')
                    if not strat_df.empty:
                        max_bottom_depth = strat_df['底部深度_m'].max()
                        bottom_depth_m = max_bottom_depth
                        print(f"✓ 导眼辅助线bottomDepth_m和totalDepth_m均缺失，使用地层最大深度: {bottom_depth_m}m")
                    else:
                        print("⚠️ 无法获取导眼辅助线bottomDepth_m的默认值，跳过绘制")
                        return None
                except Exception as e:
                    print(f"⚠️ 读取地层最大深度失败: {e}，跳过导眼辅助线绘制")
                    return None
        
        # 加载地层映射数据进行深度映射
        # 使用main.py中的HoleSectionsExtractor类
        from main import HoleSectionsExtractor
        extractor = HoleSectionsExtractor(self.well_data_json)
        stratigraphy_mapping = extractor.load_stratigraphy_mapping("stratigraphy.csv")
        
        # 映射深度
        if use_kickoff_mapped:
            # 直接使用造斜点的映射值
            mapped_top_cm = kickoff_mapped_cm
        else:
            mapped_top_cm = extractor.calculate_mapped_depth(top_depth_m, stratigraphy_mapping)
        mapped_bottom_cm = extractor.calculate_mapped_depth(bottom_depth_m, stratigraphy_mapping)
        
        # 将直径从毫米转换为厘米，再除以20进行映射
        diameter_cm = diameter_mm / 10
        mapped_diameter_cm = diameter_cm / 20
        
        # 检查是否高亮显示
        highlight = pilot_hole_data.get('highlight', False)
        
        print(f"✓ 导眼辅助线数据已加载并映射:")
        if use_kickoff_mapped:
            print(f"  起始深度: 使用造斜点映射值 -> {mapped_top_cm:.4f}cm")
        else:
            print(f"  起始深度: {top_depth_m}m -> {mapped_top_cm:.4f}cm")
        print(f"  结束深度: {bottom_depth_m}m -> {mapped_bottom_cm:.4f}cm")
        print(f"  直径: {diameter_mm}mm -> {mapped_diameter_cm:.4f}cm (映射后)")
        print(f"  高亮显示: {highlight}")
        
        return {
            'top_depth_m': top_depth_m,
            'bottom_depth_m': bottom_depth_m,
            'mapped_top_cm': mapped_top_cm,
            'mapped_bottom_cm': mapped_bottom_cm,
            'mapped_diameter_cm': mapped_diameter_cm,
            'highlight': highlight
        }
    
    def draw_wellbore(self, ax, hole_sections_df: pd.DataFrame,
                     origin_x: float, origin_y: float, kickoff_depth: float,
                     aux_x: float, aux_y: float, radius: float, deviation_angle_rad: float,
                     a_x: float, a_y: float, b_x: float, b_y: float,
                     extend_x: float, extend_y: float):
        """
        绘制井筒

        Args:
            ax: matplotlib轴对象
            hole_sections_df: 井筒段数据DataFrame
            origin_x, origin_y: 原点坐标
            kickoff_depth: 造斜点深度
            aux_x, aux_y: 辅助原点坐标
            radius: 圆弧半径
            deviation_angle_rad: 井斜角度（弧度）
            a_x, a_y: A点坐标
            b_x, b_y: B点坐标
            extend_x, extend_y: 延长终点坐标
        """
        # 按映射顶部深度排序
        hole_sections_sorted = hole_sections_df.sort_values('映射顶部_cm').reset_index(drop=True)

        # 计算井眼轨迹的最终深度（延长线末端）
        trajectory_end_depth = extend_y

        # 取最后一段井筒的直径，作为造斜点以下的统一井眼尺寸
        last_diameter = float(hole_sections_sorted['映射直径_cm'].iloc[-1]) if len(hole_sections_sorted) > 0 else 0.1

        # 先绘制造斜点以上（垂直段），仍按CSV逐段绘制
        for _, section in hole_sections_sorted.iterrows():
            top_depth = float(section['映射顶部_cm'])
            bottom_depth = float(section['映射底部_cm'])
            diameter = float(section['映射直径_cm'])

            # 完全位于造斜点以上
            if bottom_depth <= kickoff_depth:
                self.draw_vertical_wellbore_section(ax, origin_x, top_depth, bottom_depth, diameter)
            # 跨越造斜点：仅绘制到造斜点为止，以下部分忽略
            elif top_depth < kickoff_depth and bottom_depth > kickoff_depth:
                self.draw_vertical_wellbore_section(ax, origin_x, top_depth, kickoff_depth, diameter)

        # 如果是直井，不绘制造斜点以下的内容
        if self.well_type == "straight well":
            print("✓ 直井模式：不绘制造斜点以下的井筒内容")
        else:
            # 再绘制造斜点以下：不再参考CSV，使用最后一段井筒尺寸，
            # 从造斜点开始，先沿圆弧到A点，再沿稳斜段到红色虚线末端
            curved_end = max(a_y, kickoff_depth)
            curved_endpoints = None
            if curved_end > kickoff_depth:
                curved_endpoints = self.draw_curved_wellbore_section(
                    ax, aux_x, aux_y, radius, deviation_angle_rad,
                    kickoff_depth, curved_end, last_diameter
                )

            inclined_start = max(a_y, kickoff_depth)
            if self.is_horizontal_well:
                if curved_endpoints:
                    self.draw_horizontal_wellbore_extension(ax, curved_endpoints, extend_x)
            else:
                if trajectory_end_depth > inclined_start:
                    self.draw_inclined_wellbore_section(
                        ax, a_x, a_y, b_x, b_y, extend_x, extend_y,
                        inclined_start, trajectory_end_depth, last_diameter, deviation_angle_rad
                    )
        
        # 绘制导眼辅助线（如果需要）
        self.draw_pilot_hole_guide_line(ax, origin_x, origin_y, kickoff_depth,
                                       aux_x, aux_y, radius, deviation_angle_rad,
                                       a_x, a_y, b_x, b_y, extend_x, extend_y)

    def draw_pilot_hole_guide_line(self, ax, origin_x: float, origin_y: float, kickoff_depth: float,
                                   aux_x: float, aux_y: float, radius: float, deviation_angle_rad: float,
                                   a_x: float, a_y: float, b_x: float, b_y: float,
                                   extend_x: float, extend_y: float):
        """
        绘制导眼辅助线（竖直垂线）
        
        Args:
            ax: matplotlib轴对象
            origin_x, origin_y: 原点坐标
            kickoff_depth: 造斜点深度
            aux_x, aux_y: 辅助原点坐标
            radius: 圆弧半径
            deviation_angle_rad: 井斜角度（弧度）
            a_x, a_y: A点坐标
            b_x, b_y: B点坐标
            extend_x, extend_y: 延长终点坐标
        """
        # 加载并映射导眼辅助线数据
        pilot_hole_data = self.load_and_map_pilot_hole_guide_line()
        
        if not pilot_hole_data:
            return
        
        # 提取映射后的数据
        top_depth = pilot_hole_data['mapped_top_cm']
        bottom_depth = pilot_hole_data['mapped_bottom_cm']
        diameter = pilot_hole_data['mapped_diameter_cm']
        half_diameter = diameter / 2
        highlight = pilot_hole_data['highlight']
        
        # 导眼辅助线始终以造斜点以上的中轴线位置（origin_x）为中心
        # 绘制两条竖直的虚线，关于origin_x对称
        left_x = origin_x - half_diameter
        right_x = origin_x + half_diameter
        
        # 根据highlight参数选择绘图样式
        if highlight:
            # 高亮模式：黑色、粗、长虚线
            color = 'black'
            linewidth = 1.2  # 线宽
            dashes = (6, 4)  # 长虚线
            alpha = 1.0
            style_desc = "黑色粗长虚线"
        else:
            # 普通模式：灰色、细、短虚线
            color = 'gray'
            linewidth = 1
            dashes = (5, 3)  # 短虚线：线段长5，间隔3
            alpha = 0.7
            style_desc = "灰色细虚线"
        
        # 绘制导眼辅助线（竖直向下）
        ax.plot([left_x, left_x], [top_depth, bottom_depth], 
               color=color, linestyle='--', linewidth=linewidth, 
               alpha=alpha, dashes=dashes)
        ax.plot([right_x, right_x], [top_depth, bottom_depth], 
               color=color, linestyle='--', linewidth=linewidth, 
               alpha=alpha, dashes=dashes)
        
        print(f"✓ 导眼辅助线已绘制（竖直垂线，{style_desc}）")

    def draw_vertical_wellbore_section(self, ax, center_x: float, top_depth: float, bottom_depth: float, diameter: float):
        """绘制垂直井筒段"""
        half_diameter = diameter / 2
        left_x = center_x - half_diameter
        right_x = center_x + half_diameter

        # 绘制井筒壁（灰色线条）
        ax.plot([left_x, left_x], [top_depth, bottom_depth], 'gray', linewidth=1)
        ax.plot([right_x, right_x], [top_depth, bottom_depth], 'gray', linewidth=1)

    def draw_curved_wellbore_section(self, ax, aux_x: float, aux_y: float, radius: float,
                                   deviation_angle_rad: float, top_depth: float, bottom_depth: float, diameter: float):
        """绘制造斜段井筒"""
        half_diameter = diameter / 2

        # 计算角度范围
        # 根据深度计算对应的角度
        def depth_to_angle(depth):
            # 精确通过反三角函数计算角度，确保端点无缝对接
            ratio = (depth - aux_y) / max(radius, 1e-9)
            ratio = np.clip(ratio, 0.0, 1.0)
            # 目标角度范围：从 π 到 π - deviation_angle_rad
            return np.pi - np.arcsin(ratio)

        start_angle = depth_to_angle(top_depth)
        end_angle = depth_to_angle(bottom_depth)

        # 生成角度数组（包含端点）
        angles = np.linspace(start_angle, end_angle, 64)

        # 计算内外壁坐标
        inner_radius = radius - half_diameter
        outer_radius = radius + half_diameter

        inner_x = aux_x + inner_radius * np.cos(angles)
        inner_y = aux_y + inner_radius * np.sin(angles)
        outer_x = aux_x + outer_radius * np.cos(angles)
        outer_y = aux_y + outer_radius * np.sin(angles)

        # 绘制井筒壁（采用圆角端点避免微小缝隙）
        line_inner, = ax.plot(inner_x, inner_y, color='gray', linewidth=1)
        line_outer, = ax.plot(outer_x, outer_y, color='gray', linewidth=1)
        try:
            line_inner.set_solid_capstyle('round'); line_inner.set_solid_joinstyle('round')
            line_outer.set_solid_capstyle('round'); line_outer.set_solid_joinstyle('round')
        except Exception:
            pass

        endpoints = {
            'inner': (float(inner_x[-1]), float(inner_y[-1])),
            'outer': (float(outer_x[-1]), float(outer_y[-1]))
        }
        return endpoints

    def draw_horizontal_wellbore_extension(self, ax, endpoints: dict, target_x: float):
        """绘制水平井筒延长段（用于水平井）"""
        if not endpoints:
            return

        for point in endpoints.values():
            end_x, end_y = point
            if abs(target_x - end_x) < 1e-6:
                continue
            line, = ax.plot([end_x, target_x], [end_y, end_y], color='gray', linewidth=1)
            try:
                line.set_solid_capstyle('round'); line.set_solid_joinstyle('round')
            except Exception:
                pass

    def draw_horizontal_casing_extension(self, ax, endpoints: dict, target_x: float, color: str, draw_head: bool = True):
        """绘制水平套管延长段（用于水平井）"""
        if not endpoints:
            return

        for point in endpoints.values():
            end_x, end_y = point
            if abs(target_x - end_x) < 1e-6:
                continue
            line, = ax.plot([end_x, target_x], [end_y, end_y], color=color, linewidth=1.5)
            try:
                line.set_solid_capstyle('round'); line.set_solid_joinstyle('round')
            except Exception:
                pass

        # 只在需要时绘制套管头标识（等腰直角三角形）
        if draw_head:
            triangle_size = 0.1  # 三角形大小
            
            # 在目标位置绘制套管头
            for key, point in endpoints.items():
                end_x, end_y = point
                if abs(target_x - end_x) < 1e-6:
                    continue
                
                # 在延长线末端绘制套管头
                if key == 'inner':
                    # 内侧套管头（向上的三角形）
                    triangle = patches.Polygon([
                        [target_x, end_y],  # 直角顶点
                        [target_x - triangle_size, end_y],  # 左角
                        [target_x, end_y - triangle_size]  # 上角
                    ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
                    ax.add_patch(triangle)
                elif key == 'outer':
                    # 外侧套管头（向下的三角形）
                    triangle = patches.Polygon([
                        [target_x, end_y],  # 直角顶点
                        [target_x - triangle_size, end_y],  # 左角
                        [target_x, end_y + triangle_size]  # 下角
                    ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
                    ax.add_patch(triangle)

    def draw_inclined_wellbore_section(self, ax, a_x: float, a_y: float, b_x: float, b_y: float,
                                     extend_x: float, extend_y: float, top_depth: float, bottom_depth: float,
                                     diameter: float, deviation_angle_rad: float):
        """绘制稳斜段井筒"""
        half_diameter = diameter / 2

        # 计算轨迹线方向向量
        line_dx = np.sin(deviation_angle_rad)
        line_dy = np.cos(deviation_angle_rad)

        # 垂直于轨迹线的方向向量
        perp_dx = -line_dy
        perp_dy = line_dx

        def depth_to_trajectory_position(depth):
            """根据深度计算在轨迹线上的实际位置"""
            if depth <= a_y:
                # A点之前，假设是直线延伸
                return a_x, depth
            elif depth <= b_y:
                # A点到B点之间，沿轨迹线插值
                depth_ratio = (depth - a_y) / (b_y - a_y)
                x = a_x + depth_ratio * (b_x - a_x)
                y = depth
                return x, y
            else:
                # B点之后，沿延长线
                depth_ratio = (depth - b_y) / (extend_y - b_y)
                x = b_x + depth_ratio * (extend_x - b_x)
                y = depth
                return x, y

        # 为了确保井筒沿着轨迹线绘制，我们需要分段绘制
        num_segments = max(10, int((bottom_depth - top_depth) * 5))  # 根据长度调整段数
        depths = np.linspace(top_depth, bottom_depth, num_segments + 1)

        left_points_x = []
        left_points_y = []
        right_points_x = []
        right_points_y = []

        for depth in depths:
            traj_x, traj_y = depth_to_trajectory_position(depth)

            # 计算该点的井筒壁位置
            left_x = traj_x + half_diameter * perp_dx
            left_y = traj_y + half_diameter * perp_dy
            right_x = traj_x - half_diameter * perp_dx
            right_y = traj_y - half_diameter * perp_dy

            left_points_x.append(left_x)
            left_points_y.append(left_y)
            right_points_x.append(right_x)
            right_points_y.append(right_y)

        # 绘制井筒壁（采用圆角端点避免微小缝隙）
        line_left, = ax.plot(left_points_x, left_points_y, color='gray', linewidth=1)
        line_right, = ax.plot(right_points_x, right_points_y, color='gray', linewidth=1)
        try:
            line_left.set_solid_capstyle('round'); line_left.set_solid_joinstyle('round')
            line_right.set_solid_capstyle('round'); line_right.set_solid_joinstyle('round')
        except Exception:
            pass

    def get_casing_colors(self, num_casings: int) -> list:
        """
        生成套管颜色（排除黑、红、蓝）
        
        Args:
            num_casings: 套管数量
            
        Returns:
            颜色列表
        """
        # 定义套管颜色（排除黑、红、蓝）
        casing_colors = [
            '#228B22',  # 森林绿
            '#FF8C00',  # 深橙色
            '#8B008B',  # 深洋红
            '#20B2AA',  # 浅海绿
            '#FF1493',  # 深粉红
            '#32CD32',  # 酸橙绿
            '#FF4500',  # 橙红色
            '#9370DB',  # 中紫色
            '#00CED1',  # 深绿松石
            '#FF6347',  # 番茄色
            '#40E0D0',  # 绿松石
            '#DA70D6',  # 兰花紫
            '#00FA9A',  # 中春绿
            '#FF69B4',  # 热粉红
            '#98FB98',  # 浅绿色
            '#F0E68C',  # 卡其色
            '#DDA0DD',  # 梅花色
            '#90EE90',  # 浅绿色
            '#FFA07A',  # 浅鲑鱼色
            '#87CEFA',  # 浅天蓝色
        ]
        
        # 如果套管数量超过预定义颜色，使用渐变色
        if num_casings <= len(casing_colors):
            return casing_colors[:num_casings]
        else:
            # 生成渐变色
            colors = []
            for i in range(num_casings):
                hue = i / num_casings
                colors.append(plt.cm.Set2(hue))
            return colors

    def draw_hanger(self, ax, center_x: float, depth: float, diameter: float, color: str):
        """
        绘制悬挂器（"田"形状）
        
        Args:
            ax: matplotlib轴对象
            center_x: 套管中心X坐标
            depth: 悬挂器深度
            diameter: 套管直径
            color: 悬挂器颜色
        """
        half_diameter = diameter / 2
        left_x = center_x - half_diameter
        right_x = center_x + half_diameter
        
        # 悬挂器大小
        hanger_size = 0.15
        
        # 左侧悬挂器（向左的"田"形状）
        left_hanger = patches.Rectangle(
            (left_x - hanger_size, depth - hanger_size/2), 
            hanger_size, hanger_size,
            linewidth=1, edgecolor=color, facecolor=color, alpha=0.8
        )
        ax.add_patch(left_hanger)
        
        # 右侧悬挂器（向右的"田"形状）
        right_hanger = patches.Rectangle(
            (right_x, depth - hanger_size/2), 
            hanger_size, hanger_size,
            linewidth=1, edgecolor=color, facecolor=color, alpha=0.8
        )
        ax.add_patch(right_hanger)

    def draw_casing_head_filling(self, ax, center_x: float, casing_bottom_depth: float, 
                               fill_top_depth: float, diameter: float, color: str):
        """
        绘制套管头向上散点填充
        
        Args:
            ax: matplotlib轴对象
            center_x: 套管中心X坐标
            casing_bottom_depth: 套管底部深度（套管头位置）
            fill_top_depth: 填充顶部深度（悬挂器深度或地面0）
            diameter: 套管直径
            color: 填充颜色（与套管头一致）
        """
        half_diameter = diameter / 2
        left_x = center_x - half_diameter
        right_x = center_x + half_diameter
        
        # 散点填充参数
        dot_spacing_x = 0.05  # X方向点间距
        dot_spacing_y = 0.1   # Y方向点间距
        triangle_size = 0.1   # 套管头三角形大小（与套管头绘制中的triangle_size一致）
        fill_width = triangle_size  # 向外填充的宽度，与套管头三角形斜边宽度一致
        
        # 在套管头左右两侧向上向外填充散点
        # 左侧散点填充（向左向外）
        for y in np.arange(fill_top_depth, casing_bottom_depth, dot_spacing_y):
            for x_offset in np.arange(0, fill_width, dot_spacing_x):
                x = left_x - x_offset
                ax.plot(x, y, 'o', color=color, markersize=1, alpha=0.6)
        
        # 右侧散点填充（向右向外）
        for y in np.arange(fill_top_depth, casing_bottom_depth, dot_spacing_y):
            for x_offset in np.arange(0, fill_width, dot_spacing_x):
                x = right_x + x_offset
                ax.plot(x, y, 'o', color=color, markersize=1, alpha=0.6)

    def draw_casing(self, ax, casing_sections_df: pd.DataFrame,
                   origin_x: float, origin_y: float, kickoff_depth: float,
                   aux_x: float, aux_y: float, radius: float, deviation_angle_rad: float,
                   a_x: float, a_y: float, b_x: float, b_y: float,
                   extend_x: float, extend_y: float):
        """
        绘制套管层次

        Args:
            ax: matplotlib轴对象
            casing_sections_df: 套管段数据DataFrame
            其他参数: 井眼轨迹相关参数
        """
        if casing_sections_df.empty:
            return

        # 按顶部深度排序
        casing_sections_sorted = casing_sections_df.sort_values('映射顶部_cm')

        # 获取套管颜色
        casing_colors = self.get_casing_colors(len(casing_sections_sorted))

        # 计算轨迹末端深度
        trajectory_end_depth = extend_y

        # 绘制每段套管
        for i, (_, row) in enumerate(casing_sections_sorted.iterrows()):
            top_depth = float(row['映射顶部_cm'])
            bottom_depth = float(row['映射底部_cm'])
            diameter = float(row['映射外径_cm'])
            color = casing_colors[i]

            # 如果是最后一趟套管且底深超过造斜点，延长到井底
            if i == len(casing_sections_sorted) - 1 and bottom_depth > kickoff_depth:
                bottom_depth = max(bottom_depth, trajectory_end_depth)

            # 判断是否为最后一开次套管
            is_last_casing = (i == len(casing_sections_sorted) - 1)

            # 检查是否需要绘制悬挂器（套管不是从井深0米开始）
            need_hanger = (top_depth > 0)

            # 造斜点以上：绘制垂直套管
            if bottom_depth <= kickoff_depth:
                # 直井情况下，所有套管都显示套管头；非直井情况下，最后一开次套管不显示套管头
                if self.well_type == "straight well":
                    draw_head = True  # 直井：所有套管都显示套管头
                else:
                    draw_head = not is_last_casing  # 非直井：最后一开次套管不显示套管头
                self.draw_vertical_casing_section(ax, origin_x, top_depth, bottom_depth, diameter, color, draw_head)
                
                # 如果需要悬挂器，在套管起始位置绘制
                if need_hanger:
                    self.draw_hanger(ax, origin_x, top_depth, diameter, color)
                
                # 绘制套管头向上散点填充（造斜点以上井段）
                if draw_head:  # 只有显示套管头时才填充
                    # 确定填充顶部深度：如果有悬挂器则到悬挂器，否则到地面
                    fill_top_depth = top_depth if need_hanger else 0
                    self.draw_casing_head_filling(ax, origin_x, bottom_depth, fill_top_depth, diameter, color)
                    
            elif top_depth < kickoff_depth and bottom_depth > kickoff_depth:
                # 跨越造斜点的套管段，分段绘制
                # 垂直段：顶部到造斜点
                if self.well_type == "straight well":
                    draw_head = True  # 直井：所有套管都显示套管头
                else:
                    draw_head = not is_last_casing  # 非直井：最后一开次套管不显示套管头
                self.draw_vertical_casing_section(ax, origin_x, top_depth, kickoff_depth, diameter, color, draw_head)
                
                # 如果需要悬挂器，在套管起始位置绘制
                if need_hanger:
                    self.draw_hanger(ax, origin_x, top_depth, diameter, color)
                
                # 绘制套管头向上散点填充（造斜点以上井段）
                if draw_head:  # 只有显示套管头时才填充
                    # 确定填充顶部深度：如果有悬挂器则到悬挂器，否则到地面
                    fill_top_depth = top_depth if need_hanger else 0
                    self.draw_casing_head_filling(ax, origin_x, kickoff_depth, fill_top_depth, diameter, color)

                # 造斜点以下：如果是最后一趟套管，延长到井底
                if is_last_casing and self.well_type != "straight well":
                    # 造斜段（不显示套管头）
                    curved_endpoints = None
                    curved_end = max(a_y, kickoff_depth)
                    if curved_end > kickoff_depth:
                        curved_endpoints = self.draw_curved_casing_section(
                            ax, aux_x, aux_y, radius, deviation_angle_rad,
                            kickoff_depth, curved_end, diameter, color, False
                        )

                    # 稳斜段（只在最底部显示套管头）
                    if self.is_horizontal_well:
                        if curved_endpoints:
                            self.draw_horizontal_casing_extension(ax, curved_endpoints, extend_x, color, True)
                    else:
                        inclined_start = max(a_y, kickoff_depth)
                        if trajectory_end_depth > inclined_start:
                            self.draw_inclined_casing_section(
                                ax, a_x, a_y, b_x, b_y, extend_x, extend_y,
                                inclined_start, trajectory_end_depth, diameter, deviation_angle_rad, color, True
                            )
            elif top_depth >= kickoff_depth and self.well_type != "straight well":
                # 完全在造斜点以下的套管段，如果是最后一趟，延长到井底
                if is_last_casing:
                    # 造斜段（不显示套管头）
                    curved_endpoints = None
                    curved_end = max(a_y, top_depth)
                    if curved_end > top_depth and top_depth < a_y:
                        curved_endpoints = self.draw_curved_casing_section(
                            ax, aux_x, aux_y, radius, deviation_angle_rad,
                            top_depth, curved_end, diameter, color, False
                        )

                    # 稳斜段（只在最底部显示套管头）
                    if self.is_horizontal_well:
                        if curved_endpoints:
                            self.draw_horizontal_casing_extension(ax, curved_endpoints, extend_x, color, True)
                    else:
                        inclined_start = max(a_y, top_depth)
                        if trajectory_end_depth > inclined_start:
                            self.draw_inclined_casing_section(
                                ax, a_x, a_y, b_x, b_y, extend_x, extend_y,
                                inclined_start, trajectory_end_depth, diameter, deviation_angle_rad, color, True
                            )

    def draw_vertical_casing_section(self, ax, center_x: float, top_depth: float, bottom_depth: float, diameter: float, color: str, draw_head: bool = True):
        """绘制垂直段套管"""
        half_diameter = diameter / 2
        left_x = center_x - half_diameter
        right_x = center_x + half_diameter

        # 绘制套管壁（使用指定颜色）
        ax.plot([left_x, left_x], [top_depth, bottom_depth], color=color, linewidth=1.5)
        ax.plot([right_x, right_x], [top_depth, bottom_depth], color=color, linewidth=1.5)
        
        # 只在需要时绘制套管头标识（等腰直角三角形）
        if draw_head:
            triangle_size = 0.1  # 三角形大小
            
            # 左侧套管头（向左的三角形）
            left_triangle = patches.Polygon([
                [left_x, bottom_depth],  # 直角顶点
                [left_x - triangle_size, bottom_depth],  # 左下角
                [left_x, bottom_depth - triangle_size]  # 左上角
            ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
            ax.add_patch(left_triangle)
            
            # 右侧套管头（向右的三角形）
            right_triangle = patches.Polygon([
                [right_x, bottom_depth],  # 直角顶点
                [right_x + triangle_size, bottom_depth],  # 右下角
                [right_x, bottom_depth - triangle_size]  # 右上角
            ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
            ax.add_patch(right_triangle)

    def draw_curved_casing_section(self, ax, aux_x: float, aux_y: float, radius: float,
                                  deviation_angle_rad: float, top_depth: float, bottom_depth: float, diameter: float, color: str, draw_head: bool = True):
        """绘制造斜段套管"""
        half_diameter = diameter / 2

        def depth_to_angle(depth):
            # 精确通过反三角函数计算角度，确保端点无缝对接
            ratio = (depth - aux_y) / max(radius, 1e-9)
            ratio = np.clip(ratio, 0.0, 1.0)
            # 目标角度范围：从 π 到 π - deviation_angle_rad
            return np.pi - np.arcsin(ratio)

        start_angle = depth_to_angle(top_depth)
        end_angle = depth_to_angle(bottom_depth)

        # 生成角度数组（包含端点）
        angles = np.linspace(start_angle, end_angle, 64)

        # 计算内外壁坐标
        inner_radius = radius - half_diameter
        outer_radius = radius + half_diameter

        inner_x = aux_x + inner_radius * np.cos(angles)
        inner_y = aux_y + inner_radius * np.sin(angles)
        outer_x = aux_x + outer_radius * np.cos(angles)
        outer_y = aux_y + outer_radius * np.sin(angles)

        # 绘制套管壁（使用指定颜色，采用圆角端点避免微小缝隙）
        line_inner, = ax.plot(inner_x, inner_y, color=color, linewidth=1.5)
        line_outer, = ax.plot(outer_x, outer_y, color=color, linewidth=1.5)
        try:
            line_inner.set_solid_capstyle('round'); line_inner.set_solid_joinstyle('round')
            line_outer.set_solid_capstyle('round'); line_outer.set_solid_joinstyle('round')
        except Exception:
            pass

        endpoints = {
            'inner': (float(inner_x[-1]), float(inner_y[-1])),
            'outer': (float(outer_x[-1]), float(outer_y[-1]))
        }
        
        # 只在需要时绘制套管头标识（等腰直角三角形）
        if draw_head:
            triangle_size = 0.1  # 三角形大小
            
            # 内壁套管头（向内的三角形）
            inner_end_x = inner_x[-1]
            inner_end_y = inner_y[-1]
            # 计算内壁在终点处的切线方向
            if len(inner_x) >= 2:
                inner_dx = inner_x[-1] - inner_x[-2]
                inner_dy = inner_y[-1] - inner_y[-2]
                inner_length = np.sqrt(inner_dx**2 + inner_dy**2)
                if inner_length > 0:
                    inner_dx /= inner_length
                    inner_dy /= inner_length
                    # 垂直于切线的方向（向内）
                    inner_perp_dx = -inner_dy
                    inner_perp_dy = inner_dx
                    
                    inner_triangle = patches.Polygon([
                        [inner_end_x, inner_end_y],  # 直角顶点
                        [inner_end_x + inner_perp_dx * triangle_size, inner_end_y + inner_perp_dy * triangle_size],  # 内角
                        [inner_end_x - inner_dx * triangle_size, inner_end_y - inner_dy * triangle_size]  # 沿切线方向
                    ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
                    ax.add_patch(inner_triangle)
            
            # 外壁套管头（向外的三角形）
            outer_end_x = outer_x[-1]
            outer_end_y = outer_y[-1]
            # 计算外壁在终点处的切线方向
            if len(outer_x) >= 2:
                outer_dx = outer_x[-1] - outer_x[-2]
                outer_dy = outer_y[-1] - outer_y[-2]
                outer_length = np.sqrt(outer_dx**2 + outer_dy**2)
                if outer_length > 0:
                    outer_dx /= outer_length
                    outer_dy /= outer_length
                    # 垂直于切线的方向（向外）
                    outer_perp_dx = outer_dy
                    outer_perp_dy = -outer_dx
                    
                    outer_triangle = patches.Polygon([
                        [outer_end_x, outer_end_y],  # 直角顶点
                        [outer_end_x + outer_perp_dx * triangle_size, outer_end_y + outer_perp_dy * triangle_size],  # 外角
                        [outer_end_x - outer_dx * triangle_size, outer_end_y - outer_dy * triangle_size]  # 沿切线方向
                    ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
                    ax.add_patch(outer_triangle)

        return endpoints

    def draw_inclined_casing_section(self, ax, a_x: float, a_y: float, b_x: float, b_y: float,
                                    extend_x: float, extend_y: float, top_depth: float, bottom_depth: float,
                                    diameter: float, deviation_angle_rad: float, color: str, draw_head: bool = True):
        """绘制稳斜段套管"""
        half_diameter = diameter / 2

        # 计算轨迹线方向向量
        line_dx = np.sin(deviation_angle_rad)
        line_dy = np.cos(deviation_angle_rad)

        # 垂直于轨迹线的方向向量
        perp_dx = -line_dy
        perp_dy = line_dx

        def depth_to_trajectory_position(depth):
            """根据深度计算在轨迹线上的实际位置"""
            if depth <= a_y:
                # A点之前，假设是直线延伸
                return a_x, depth
            elif depth <= b_y:
                # A点到B点之间，沿轨迹线插值
                depth_ratio = (depth - a_y) / (b_y - a_y)
                x = a_x + depth_ratio * (b_x - a_x)
                y = depth
                return x, y
            else:
                # B点之后，沿延长线
                depth_ratio = (depth - b_y) / (extend_y - b_y)
                x = b_x + depth_ratio * (extend_x - b_x)
                y = depth
                return x, y

        # 为了确保套管沿着轨迹线绘制，我们需要分段绘制
        num_segments = max(10, int((bottom_depth - top_depth) * 5))  # 根据长度调整段数
        depths = np.linspace(top_depth, bottom_depth, num_segments + 1)

        left_points_x = []
        left_points_y = []
        right_points_x = []
        right_points_y = []

        for depth in depths:
            traj_x, traj_y = depth_to_trajectory_position(depth)

            # 计算该点的套管壁位置
            left_x = traj_x + half_diameter * perp_dx
            left_y = traj_y + half_diameter * perp_dy
            right_x = traj_x - half_diameter * perp_dx
            right_y = traj_y - half_diameter * perp_dy

            left_points_x.append(left_x)
            left_points_y.append(left_y)
            right_points_x.append(right_x)
            right_points_y.append(right_y)

        # 绘制套管壁（使用指定颜色，采用圆角端点避免微小缝隙）
        line_left, = ax.plot(left_points_x, left_points_y, color=color, linewidth=1.5)
        line_right, = ax.plot(right_points_x, right_points_y, color=color, linewidth=1.5)
        try:
            line_left.set_solid_capstyle('round'); line_left.set_solid_joinstyle('round')
            line_right.set_solid_capstyle('round'); line_right.set_solid_capstyle('round')
        except Exception:
            pass
        
        # 只在需要时绘制套管头标识（等腰直角三角形）
        if draw_head:
            triangle_size = 0.1  # 三角形大小
            
            # 左侧套管头（向左的三角形）
            left_end_x = left_points_x[-1]
            left_end_y = left_points_y[-1]
            # 计算左侧套管在终点处的切线方向
            if len(left_points_x) >= 2:
                left_dx = left_points_x[-1] - left_points_x[-2]
                left_dy = left_points_y[-1] - left_points_y[-2]
                left_length = np.sqrt(left_dx**2 + left_dy**2)
                if left_length > 0:
                    left_dx /= left_length
                    left_dy /= left_length
                    # 垂直于切线的方向（向左）
                    left_perp_dx = -left_dy
                    left_perp_dy = left_dx
                    
                    left_triangle = patches.Polygon([
                        [left_end_x, left_end_y],  # 直角顶点
                        [left_end_x + left_perp_dx * triangle_size, left_end_y + left_perp_dy * triangle_size],  # 左角
                        [left_end_x - left_dx * triangle_size, left_end_y - left_dy * triangle_size]  # 沿切线方向
                    ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
                    ax.add_patch(left_triangle)
            
            # 右侧套管头（向右的三角形）
            right_end_x = right_points_x[-1]
            right_end_y = right_points_y[-1]
            # 计算右侧套管在终点处的切线方向
            if len(right_points_x) >= 2:
                right_dx = right_points_x[-1] - right_points_x[-2]
                right_dy = right_points_y[-1] - right_points_y[-2]
                right_length = np.sqrt(right_dx**2 + right_dy**2)
                if right_length > 0:
                    right_dx /= right_length
                    right_dy /= right_length
                    # 垂直于切线的方向（向右）
                    right_perp_dx = right_dy
                    right_perp_dy = -right_dx
                    
                    right_triangle = patches.Polygon([
                        [right_end_x, right_end_y],  # 直角顶点
                        [right_end_x + right_perp_dx * triangle_size, right_end_y + right_perp_dy * triangle_size],  # 右角
                        [right_end_x - right_dx * triangle_size, right_end_y - right_dy * triangle_size]  # 沿切线方向
                    ], closed=True, facecolor=color, edgecolor=color, linewidth=0.5)
                    ax.add_patch(right_triangle)

    def draw_hole_and_casing_notes(self, ax, hole_sections_df: pd.DataFrame, casing_sections_df: pd.DataFrame, total_height_cm: float, a_y: float = None, kickoff_depth: float = None):
        """
        绘制井筒和套管备注标注
        
        Args:
            ax: matplotlib轴对象
            hole_sections_df: 井筒段数据DataFrame
            casing_sections_df: 套管段数据DataFrame
            total_height_cm: 总高度
            a_y: A靶点深度（用于套管备注位置计算）
            kickoff_depth: 造斜点深度（用于水平井套管备注位置计算）
        """
        # 井身结构区的起始X位置
        trajectory_start_x = self.layer_width_cm + self.drilling_fluid_width_cm
        
        # 绘制井筒备注（靠近井筒）- 根据配置决定是否显示
        if self.legend_config.get('holeLegend', True) and not hole_sections_df.empty:
            hole_sections_sorted = hole_sections_df.sort_values('映射顶部_cm')
            for _, row in hole_sections_sorted.iterrows():
                top_depth = float(row['映射顶部_cm'])
                bottom_depth = float(row['映射底部_cm'])
                note = str(row['备注_in'])
                
                # 计算备注位置（井段中部偏下）
                note_y = top_depth + (bottom_depth - top_depth) * 0.6
                
                if self.is_horizontal_well:
                    # horizontal well：中轴线位于1/3处
                    center_x = trajectory_start_x + self.trajectory_width_cm / 3
                    # 井筒备注固定在左边框线和中轴线的1/2处
                    note_x = trajectory_start_x + (center_x - trajectory_start_x) / 2
                else:
                    # 其他井型：中轴线位于中点
                    center_x = trajectory_start_x + self.trajectory_width_cm / 2
                    # 井筒备注固定在左边框线和中轴线的1/2处
                    note_x = trajectory_start_x + (center_x - trajectory_start_x) / 2
                
                # 绘制井筒备注（左对齐）
                ax.text(note_x, note_y, f"井筒: {note}", 
                       ha='left', va='center', fontsize=8, color='gray', weight='bold')
        
        # 绘制套管备注（靠近井筒）- 根据配置决定是否显示
        if self.legend_config.get('casingLegend', True) and not casing_sections_df.empty:
            casing_sections_sorted = casing_sections_df.sort_values('映射顶部_cm')
            casing_colors = self.get_casing_colors(len(casing_sections_sorted))
            
            for i, (_, row) in enumerate(casing_sections_sorted.iterrows()):
                top_depth = float(row['映射顶部_cm'])
                bottom_depth = float(row['映射底部_cm'])
                note = str(row['备注_in'])
                color = casing_colors[i]
                
                # 计算备注位置（井段中部偏下）
                # 如果套管底深超过A靶点，备注位置与A靶点齐平
                if a_y is not None and bottom_depth > a_y:
                    # 如果是水平井，将A点处的套管备注位置改到造斜点处
                    if self.is_horizontal_well and kickoff_depth is not None:
                        note_y = kickoff_depth
                    else:
                        note_y = a_y
                else:
                    note_y = top_depth + (bottom_depth - top_depth) * 0.6
                
                if self.is_horizontal_well or self.well_type == "deviated well":
                    # horizontal well和deviated well：中轴线位于1/3处
                    center_x = trajectory_start_x + self.trajectory_width_cm / 3
                    # 套管备注固定在中轴线和右边框线的1/2处（关于中轴线对称）
                    right_edge_x = trajectory_start_x + self.trajectory_width_cm
                    note_x = center_x + (right_edge_x - center_x) / 2
                else:
                    # straight well：中轴线位于中点
                    center_x = trajectory_start_x + self.trajectory_width_cm / 2
                    # 套管备注固定在中轴线和右边框线的1/2处（关于中轴线对称）
                    right_edge_x = trajectory_start_x + self.trajectory_width_cm
                    note_x = center_x + (right_edge_x - center_x) / 2
                
                # 绘制套管备注（左对齐）
                ax.text(note_x, note_y, f"套管: {note}", 
                       ha='left', va='center', fontsize=8, color=color, weight='bold')

    def draw_depth_legend(self, ax, deviation_df: pd.DataFrame, total_height_cm: float):
        """
        绘制深度图例（造斜点、A点、B点）
        
        Args:
            ax: matplotlib轴对象
            deviation_df: 井眼轨迹数据DataFrame
            total_height_cm: 总高度
        """
        # 井身结构区的起始X位置
        trajectory_start_x = self.layer_width_cm + self.drilling_fluid_width_cm
        
        # 从井眼轨迹数据中提取深度信息
        depth_data = {}
        for _, row in deviation_df.iterrows():
            param_name = row['参数名称']
            value = row['数值_m']  # 实际深度（m）
            # 处理null值：如果是字符串'null'或者空值，则不添加到depth_data
            if value != 'null' and value != '' and value is not None and str(value).lower() != 'null':
                if param_name == '造斜点深度':
                    depth_data['kickoff_depth'] = value
                elif param_name == '目标点A深度':
                    depth_data['target_a_depth'] = value
                elif param_name == '目标点B深度':
                    depth_data['target_b_depth'] = value
                elif param_name == '真实造斜点深度':
                    depth_data['real_kickoff_depth'] = value
        
        # 绘制深度图例（关键点图例）
        if self.is_horizontal_well or self.well_type == "deviated well":
            # horizontal well和deviated well：中轴线位于1/3处
            center_x = trajectory_start_x + self.trajectory_width_cm / 3
            # 关键点图例固定在左边框线和中轴线的1/2处
            legend_x = trajectory_start_x + (center_x - trajectory_start_x) / 2 + 0.5
        else:
            # straight well：中轴线位于中点
            center_x = trajectory_start_x + self.trajectory_width_cm / 2
            # 关键点图例固定在左边框线和中轴线的1/2处
            legend_x = trajectory_start_x + (center_x - trajectory_start_x) / 2 + 0.5
        legend_y_start = total_height_cm - 0.5  # 从顶部开始
        
        
        # 根据配置决定是否显示各个图例
        if self.legend_config.get('targetPointsLegend', True) and 'target_b_depth' in depth_data:
            ax.text(legend_x, legend_y_start, f"B: {depth_data['target_b_depth']}m", 
                   ha='right', va='center', fontsize=9, color='red', weight='bold')
            legend_y_start -= 0.3
        
        if self.legend_config.get('targetPointsLegend', True) and 'target_a_depth' in depth_data:
            ax.text(legend_x, legend_y_start, f"A: {depth_data['target_a_depth']}m", 
                   ha='right', va='center', fontsize=9, color='red', weight='bold')
            legend_y_start -= 0.3
        
        if self.legend_config.get('kickoffLegend', True) and 'real_kickoff_depth' in depth_data:
            # 根据侧钻状态选择图例文字和颜色
            if self.is_side_tracking:
                # 侧钻：侧钻点，黑色
                ax.text(legend_x, legend_y_start, f"侧钻点: {depth_data['real_kickoff_depth']}m", 
                       ha='right', va='center', fontsize=9, color='black', weight='bold')
            else:
                # 造斜：造斜点，蓝色
                ax.text(legend_x, legend_y_start, f"造斜点: {depth_data['real_kickoff_depth']}m", 
                       ha='right', va='center', fontsize=9, color='blue', weight='bold')

    def process(self):
        """
        执行绘图流程
        """
        try:
            print(f"开始处理文件:")
            print(f"  地层数据: {self.stratigraphy_csv}")
            print(f"  钻井液数据: {self.drilling_fluid_csv}")
            print(f"  井眼轨迹数据: {self.deviation_csv}")
            print(f"  井筒段数据: {self.hole_sections_csv}")
            print(f"  井数据: {self.well_data_json}")

            # 加载井数据并检测井类型
            well_data = self.load_well_data()
            self.well_type = self.detect_well_type(well_data)
            print(f"✓ 检测到井类型: {self.well_type}")
            
            # 根据井类型调整绘图区宽度
            self.adjust_trajectory_width()
            if self.is_horizontal_well:
                print(f"✓ horizontal well模式：井身结构绘图区宽度调整为 {self.trajectory_width_cm}cm")
            elif self.well_type == "deviated well":
                print(f"✓ deviated well模式：井身结构绘图区宽度调整为 {self.trajectory_width_cm}cm")

            # 加载数据
            strat_df = self.load_stratigraphy_data()
            fluid_df = self.load_drilling_fluid_data()
            deviation_df = self.load_deviation_data()
            hole_sections_df = self.load_hole_sections_data()
            casing_sections_df = self.load_casing_sections_data()

            # 生成组合图
            print("\n生成地层分层图、钻井液设计图、井眼轨迹图、井筒和套管...")
            self.create_combined_plot(strat_df, fluid_df, deviation_df, hole_sections_df, casing_sections_df, "well_structure_plot.png")

            print("\n绘图完成！")

        except Exception as e:
            print(f"❌ 绘图失败: {e}")


def main():
    """主函数"""
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1:
        stratigraphy_csv = sys.argv[1]
    else:
        stratigraphy_csv = "stratigraphy.csv"

    if len(sys.argv) > 2:
        drilling_fluid_csv = sys.argv[2]
    else:
        drilling_fluid_csv = "drilling_fluid_pressure.csv"

    if len(sys.argv) > 3:
        deviation_csv = sys.argv[3]
    else:
        deviation_csv = "deviationData.csv"

    if len(sys.argv) > 4:
        hole_sections_csv = sys.argv[4]
    else:
        hole_sections_csv = "hole_sections.csv"

    if len(sys.argv) > 5:
        casing_sections_csv = sys.argv[5]
    else:
        casing_sections_csv = "casing_sections.csv"

    if len(sys.argv) > 6:
        well_data_json = sys.argv[6]
    else:
        well_data_json = "well_data.json"

    # 创建绘图器并处理
    plotter = StratigraphyPlotter(stratigraphy_csv, drilling_fluid_csv, deviation_csv, hole_sections_csv, casing_sections_csv, well_data_json)
    plotter.process()


if __name__ == "__main__":
    main()
