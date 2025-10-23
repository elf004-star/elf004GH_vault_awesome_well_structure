"""
awesome well structure MCP 服务（井身结构示意图MCP） 

基于井数据生成井身结构图的服务
"""

import json
import subprocess
import os
import shutil
import time
import glob
import importlib.util
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("awesome_well_MCP")


def validate_well_data(data: Dict[str, Any]) -> bool:
    """验证井数据完整性"""
    required_fields = [
        "wellName", "totalDepth_m", "wellType", 
        "stratigraphy", "drillingFluidAndPressure", "wellboreStructure"
    ]
    
    for field in required_fields:
        if field not in data:
            return False
    
    # 验证井型
    if data["wellType"] not in ["straight well", "deviated well", "horizontal well", "straight-to-horizontal well"]:
        return False
    
    # 验证深度数据
    if not isinstance(data["totalDepth_m"], (int, float)) or data["totalDepth_m"] <= 0:
        return False
    
    return True


def update_well_data_file(data: Dict[str, Any]) -> bool:
    """更新well_data.json文件"""
    try:
        # 创建备份
        backup_path = Path("well_data_stadio.json")
        if Path("well_data.json").exists():
            shutil.copy2("well_data.json", backup_path)
        
        # 写入新数据
        with open("well_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"更新井数据文件失败: {e}")
        return False


def run_well_generator() -> bool:
    """启动井身结构生成器并检测PNG和报告文件生成"""
    try:
        # 首先尝试在当前目录查找
        generator_path = Path("WellStructure.exe")
        if not generator_path.exists():
            # 如果当前目录没有，尝试在包目录中查找
            try:
                spec = importlib.util.find_spec("awesome_well_mcp")
                if spec is not None and spec.origin is not None:
                    package_dir = Path(spec.origin).parent
                    generator_path = package_dir / "WellStructure.exe"
                    if not generator_path.exists():
                        print("WellStructure.exe 不存在")
                        return False
                else:
                    print("WellStructure.exe 不存在")
                    return False
            except Exception:
                print("WellStructure.exe 不存在")
                return False
        
        # 1. 启动前先清理所有生成的文件
        print("清理现有生成文件...")
        cleanup_generated_files()
        
        # 2. 启动exe程序
        print("启动井身结构生成器...")
        process = subprocess.Popen([str(generator_path)])
        print(f"井身结构生成器已启动，进程ID: {process.pid}")
        
        # 3. 检测PNG图片生成
        if not wait_for_png_generation():
            print("PNG图片生成检测失败")
            return False
        
        # 4. 检测报告文件生成
        if not wait_for_report_generation():
            print("报告文件生成检测失败")
            return False
        
        # 5. 检测成功后等待6秒，然后继续
        print("检测成功，等待6秒后继续...")
        time.sleep(6)
        
        return True
    except Exception as e:
        print(f"启动生成器失败: {e}")
        return False


def create_timestamp_folder() -> str:
    """创建时间戳文件夹"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_path = Path(timestamp)
        folder_path.mkdir(exist_ok=True)
        return str(folder_path)
    except Exception as e:
        print(f"创建时间戳文件夹失败: {e}")
        return ""

def move_generated_files(folder_path: str) -> bool:
    """按顺序移动生成的文件到时间戳文件夹"""
    try:
        if not folder_path:
            return False
        
        target_folder = Path(folder_path)
        if not target_folder.exists():
            return False
        
        moved_files = []
        
        # 1. 移动PNG文件
        png_files = ["well_info.png", "well_structure_plot.png"]
        for filename in png_files:
            source_file = Path(filename)
            if source_file.exists():
                target_file = target_folder / filename
                shutil.move(str(source_file), str(target_file))
                moved_files.append(filename)
                print(f"已移动PNG文件: {filename}")
        
        # 2. 移动CSV文件
        csv_files = [
            "stratigraphy.csv",
            "stratigraphy_raw.csv",
            "casing_sections.csv", 
            "casing_sections_raw.csv",
            "hole_sections.csv",
            "hole_sections_raw.csv",
            "drilling_fluid_pressure.csv",
            "drilling_fluid_pressure_raw.csv",
            "deviationData.csv",
            "deviationData_raw.csv",
            "location.csv"
        ]
        for filename in csv_files:
            source_file = Path(filename)
            if source_file.exists():
                target_file = target_folder / filename
                shutil.move(str(source_file), str(target_file))
                moved_files.append(filename)
                print(f"已移动CSV文件: {filename}")
        
        # 3. 移动JSON文件
        json_files = ["well_data.json", "well_data_backup.json"]
        for filename in json_files:
            source_file = Path(filename)
            if source_file.exists():
                target_file = target_folder / filename
                shutil.move(str(source_file), str(target_file))
                moved_files.append(filename)
                print(f"已移动JSON文件: {filename}")
        
        # 4. 移动MD文件（最后移动）
        md_files = ["well_structure_report.md"]
        for filename in md_files:
            source_file = Path(filename)
            if source_file.exists():
                target_file = target_folder / filename
                shutil.move(str(source_file), str(target_file))
                moved_files.append(filename)
                print(f"已移动MD文件: {filename}")
        
        print(f"已移动 {len(moved_files)} 个文件到文件夹: {folder_path}")
        return True
        
    except Exception as e:
        print(f"移动文件失败: {e}")
        return False


def read_report_content(report_path: str) -> str:
    """读取MD报告内容"""
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取报告内容失败: {e}")
        return ""

def cleanup_generated_files():
    """清理指定的生成文件"""
    try:
        cleaned_count = 0
        
        # 1. 清理报告文件
        report_file = "well_structure_report.md"
        if os.path.exists(report_file):
            try:
                os.remove(report_file)
                cleaned_count += 1
                print(f"已删除报告文件: {report_file}")
            except Exception as e:
                print(f"删除报告文件失败 {report_file}: {e}")
        
        # 2. 清理所有CSV文件
        csv_files = [
            "stratigraphy.csv",
            "stratigraphy_raw.csv",
            "casing_sections.csv",
            "casing_sections_raw.csv",
            "hole_sections.csv",
            "hole_sections_raw.csv",
            "drilling_fluid_pressure.csv",
            "drilling_fluid_pressure_raw.csv",
            "deviationData.csv",
            "deviationData_raw.csv"
        ]
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                try:
                    os.remove(csv_file)
                    cleaned_count += 1
                    print(f"已删除CSV文件: {csv_file}")
                except Exception as e:
                    print(f"删除CSV文件失败 {csv_file}: {e}")
        
        # 3. 清理指定的PNG文件
        png_files = ["well_structure_plot.png", "well_info.png"]
        for png_file in png_files:
            if os.path.exists(png_file):
                try:
                    os.remove(png_file)
                    cleaned_count += 1
                    print(f"已删除PNG文件: {png_file}")
                except Exception as e:
                    print(f"删除PNG文件失败 {png_file}: {e}")
        
        print(f"清理完成，共删除 {cleaned_count} 个文件")
        return True
    except Exception as e:
        print(f"清理生成文件失败: {e}")
        return False


def wait_for_png_generation(max_attempts: int = 36) -> bool:
    """检测PNG图片生成，每隔1秒检查一次"""
    try:
        print("开始检测PNG图片生成...")
        for attempt in range(max_attempts):
            png_files = glob.glob("well_structure_plot.png")
            if png_files:
                print(f"检测到PNG图片生成: {png_files}")
                print("exe程序启动成功")
                return True
            
            print(f"第 {attempt + 1} 次检测，未发现PNG图片，继续等待...")
            time.sleep(1)
        
        print(f"检测超时，{max_attempts} 次尝试后仍未发现PNG图片")
        return False
    except Exception as e:
        print(f"检测PNG图片生成失败: {e}")
        return False


def wait_for_report_generation(max_attempts: int = 36) -> bool:
    """检测报告文件生成，每隔1秒检查一次"""
    try:
        print("开始检测报告文件生成...")
        for attempt in range(max_attempts):
            if os.path.exists("well_structure_report.md"):
                print("检测到报告文件生成: well_structure_report.md")
                return True
            
            print(f"第 {attempt + 1} 次检测，未发现报告文件，继续等待...")
            time.sleep(1)
        
        print(f"检测超时，{max_attempts} 次尝试后仍未发现报告文件")
        return False
    except Exception as e:
        print(f"检测报告文件生成失败: {e}")
        return False


def get_folder_absolute_path(folder_path: str) -> str:
    """获取文件夹绝对路径"""
    try:
        folder = Path(folder_path)
        if folder.exists():
            return str(folder.absolute())
        else:
            print("文件夹不存在")
            return ""
    except Exception as e:
        print(f"获取文件夹路径失败: {e}")
        return ""


def format_simple_response(structure_image_path: str, info_image_path: str) -> str:
    """简化的格式化回答"""
    try:
        response = f"井身结构示意图为：\n![PNG]({structure_image_path})\n\n井身结构信息图为：\n![PNG]({info_image_path})"
        return response
    except Exception as e:
        print(f"格式化回答失败: {e}")
        return ""


def cleanup_temp_files():
    """清理临时文件"""
    try:
        # 清理备份文件
        backup_path = Path("well_data_stadio.json")
        if backup_path.exists():
            backup_path.unlink()
    except Exception as e:
        print(f"清理临时文件失败: {e}")


@mcp.tool()
def generate_well_structure(well_data: Dict[str, Any]) -> Dict[str, Any]:
    """生成井身结构示意图及相关报告。
    
    基于提供的井数据（JSON格式），调用井身结构生成器生成井身结构示意图（PNG）、
    井身结构信息图（PNG）和详细的Markdown格式报告。支持直井、定向井、水平井等
    多种井型，可配置地层、钻井液压力、井身结构等详细参数。
    
    功能描述:
        1. 接收并验证井数据的完整性和合法性
        2. 调用外部生成器程序生成井身结构可视化图表
        3. 创建带时间戳的归档文件夹保存所有生成文件
        4. 返回图片路径和详细报告内容
    
    Args:
        well_data (Dict[str, Any]): 井数据字典，必需。包含以下字段：
            
            必填字段：
                wellName (str): 井名
                totalDepth_m (float): 井深，单位：米，必须大于0
                wellType (str): 井型，可选值：
                    - "straight well": 直井
                    - "deviated well": 定向井
                    - "horizontal well": 水平井
                    - "straight-to-horizontal well": 直-水平井
                stratigraphy (List[Dict]): 地层分层信息数组
                    - name (str): 地层名称
                    - topDepth_m (float): 顶深，单位：米
                    - bottomDepth_m (float): 底深，单位：米
                    注意：相邻地层的bottomDepth_m必须等于下一地层的topDepth_m
                drillingFluidAndPressure (List[Dict]): 钻井液密度和压力剖面数组
                    - topDepth_m (float): 区间顶深，单位：米
                    - bottomDepth_m (float): 区间底深，单位：米
                    - porePressure_gcm3 (float): 孔隙压力当量密度，单位：g/cm³
                    - pressureWindow_gcm3 (Dict): 安全密度窗口
                        - min (float): 最小安全密度，单位：g/cm³
                        - max (float): 最大安全密度，单位：g/cm³
                wellboreStructure (Dict): 井身物理结构
                    - holeSections (List[Dict]): 裸眼井段数组
                        - topDepth_m (float): 井段顶深，单位：米
                        - bottomDepth_m (float): 井段底深，单位：米
                        - diameter_mm (float): 钻头直径，单位：毫米
                        - note_in (str, 可选): 备注说明
                    - casingSections (List[Dict]): 套管程序数组
                        - topDepth_m (float): 套管悬挂点深度，单位：米
                        - bottomDepth_m (float): 套管鞋深度，单位：米
                        - od_mm (float): 套管外径，单位：毫米
                        - note_in (str, 可选): 备注说明
            
            可选字段：
                deviationData (Dict): 井眼轨迹参数（非直井时建议提供）
                    - kickoffPoint_m (float): 绘图造斜点，单位：米
                    - REAL_kickoffPoint_m (float): 显示造斜点，单位：米
                    - targetPointA_m (float): A靶点井深，单位：米
                    - targetPointA_verticalDepth_m (float): A靶点垂深，单位：米
                    - targetPointB_m (float): B靶点井深，单位：米
                    - deviationAngle_deg (float): 井斜角，单位：度
                    - DistanceAB_m (float): A、B靶点距离，单位：米
                legendConfig (Dict): 图例和样式配置
                    - casingLegend (bool): 是否显示套管图例
                    - holeLegend (bool): 是否显示井筒图例
                    - kickoffLegend (bool): 是否显示造斜点图例
                    - targetPointsLegend (bool): 是否显示靶点图例
                    - fill (bool): 是否填充套管-井筒环空
                    - simpleinfo (bool): 是否使用简化信息图
                pilotHoleGuideLine (Dict): 导眼井辅助线配置，放置在wellboreStructure内。
                    - display (bool): 是否显示辅助线
                    - highlight (bool): 是否高亮显示
                    - side_tracking (bool): 是否标记为侧钻点
    
    Returns:
        Dict[str, Any]: 生成结果字典，包含以下字段：
            
            成功时 (success=True)：
                success (bool): True，表示生成成功
                report_content (str): Markdown格式的详细报告内容
                response (str): 包含图片路径的格式化响应文本
                notice (str): 使用提示信息
                well_info (Dict): 井基本信息
                    - well_name (str): 井名
                    - well_type (str): 井型
                    - total_depth (float): 井深
                archive_folder (str): 归档文件夹相对路径
                structure_image_path (str): 井身结构图绝对路径
                info_image_path (str): 井身信息图绝对路径
            
            失败时 (success=False)：
                success (bool): False，表示生成失败
                error (str): 错误描述信息
                error_code (str): 错误代码，可能的值：
                    - "VALIDATION_ERROR": 数据验证失败
                    - "FILE_UPDATE_ERROR": 文件更新失败
                    - "GENERATOR_ERROR": 生成器启动或运行失败
                    - "FOLDER_CREATION_ERROR": 文件夹创建失败
                    - "FILE_ARCHIVE_ERROR": 文件归档失败
                    - "FOLDER_PATH_ERROR": 路径获取失败
                    - "UNKNOWN_ERROR": 未知错误
                details (str): 详细错误信息
    
    Raises:
        本函数不会主动抛出异常，所有错误均通过返回字典中的success字段和error信息表示。
    
    Notes:
        - 服务端具有较强容错性，部分数据缺失时会自动生成默认值
        - 所有生成的文件会自动归档到以时间戳命名的文件夹中
        - 不要向用户复述或展示原始JSON数据，直接使用工具生成结果
        - 进行任何数据修改操作前必须提醒用户
    
    Examples:
        >>> well_data = {
        ...     "wellName": "Well_Z101",
        ...     "totalDepth_m": 6900,
        ...     "wellType": "deviated well",
        ...     "deviationData": {
        ...         "kickoffPoint_m": 3060,
        ...         "deviationAngle_deg": 30,
        ...         "targetPointA_m": 5090,
        ...         "targetPointA_verticalDepth_m": 4825,
        ...         "targetPointB_m": 6890,
        ...         "DistanceAB_m": 1800,
        ...         "REAL_kickoffPoint_m": 3060
        ...     },
        ...     "stratigraphy": [
        ...         {"name": "遂宁组", "topDepth_m": 0, "bottomDepth_m": 150},
        ...         {"name": "沙溪庙组", "topDepth_m": 150, "bottomDepth_m": 1112},
        ...         ......
        ...     ],
        ...     "drillingFluidAndPressure": [
        ...         {"topDepth_m": 0, "bottomDepth_m": 150, 
        ...          "porePressure_gcm3": 1.085, 
        ...          "pressureWindow_gcm3": {"min": 1.05, "max": 1.10}},
        ...          ......
        ...     ],
        ...     "wellboreStructure": {
        ...         "holeSections": [
        ...             {"topDepth_m": 0, "bottomDepth_m": 152, 
        ...              "diameter_mm": 660.4, "note_in": "26\\""},
        ...              ......
        ...         ],
        ...         "casingSections": [
        ...             {"topDepth_m": 0, "bottomDepth_m": 150.62, 
        ...              "od_mm": 508, "note_in": "20\\"导管"},
        ...              ......
        ...         ],
        ...         "pilotHoleGuideLine": {
        ...         "topDepth_m": 3060,
        ...         "bottomDepth_m": 6900,
        ...         "diameter_mm": 215.9,
        ...         "display": true,
        ...         "highlight": true,
        ...         "side_tracking": true
        ...         }
        ...     },
        ...     "legendConfig": {
        ...     "casingLegend": false,
        ...     "holeLegend": false,
        ...     "kickoffLegend": true,
        ...     "targetPointsLegend": true,
        ...     "fill": false,
        ...     "simpleinfo": true
        ...     }
        ... }
        >>> result = generate_well_structure(well_data)
        >>> if result["success"]:
        ...     print(f"生成成功！图片路径：{result['structure_image_path']}")
        ... else:
        ...     print(f"生成失败：{result['error']}")
    """
    try:
        # 验证数据
        if not validate_well_data(well_data):
            return {
                "success": False,
                "error": "井数据验证失败",
                "error_code": "VALIDATION_ERROR",
                "details": "缺少必需字段或数据格式不正确"
            }
        
        # 更新井数据文件
        if not update_well_data_file(well_data):
            return {
                "success": False,
                "error": "更新井数据文件失败",
                "error_code": "FILE_UPDATE_ERROR",
                "details": "无法写入well_data.json文件"
            }
        
        # 启动生成器并检测PNG生成
        if not run_well_generator():
            return {
                "success": False,
                "error": "井身结构生成器启动失败",
                "error_code": "GENERATOR_ERROR",
                "details": "生成器无法正常启动或PNG图片生成检测失败"
            }
        
        # 创建时间戳文件夹并移动生成的文件
        timestamp_folder = create_timestamp_folder()
        if not timestamp_folder:
            return {
                "success": False,
                "error": "创建归档文件夹失败",
                "error_code": "FOLDER_CREATION_ERROR",
                "details": "无法创建时间戳文件夹"
            }
        
        # 先读取MD文件内容
        report_content = read_report_content("well_structure_report.md")
        
        # 一起移动所有文件
        if not move_generated_files(timestamp_folder):
            return {
                "success": False,
                "error": "文件归档失败",
                "error_code": "FILE_ARCHIVE_ERROR",
                "details": "无法移动生成的文件到归档文件夹"
            }
        
        # 获取文件夹绝对路径
        folder_absolute_path = get_folder_absolute_path(timestamp_folder)
        if not folder_absolute_path:
            return {
                "success": False,
                "error": "获取文件夹路径失败",
                "error_code": "FOLDER_PATH_ERROR",
                "details": "无法获取归档文件夹的绝对路径"
            }
        
        # 构建图片绝对路径
        structure_image_path = f"{folder_absolute_path}\\well_structure_plot.png"
        info_image_path = f"{folder_absolute_path}\\well_info.png"
        
        # 清理临时文件
        cleanup_temp_files()
        
        # 格式化简化回答
        formatted_response = format_simple_response(structure_image_path, info_image_path)
        
        # 返回成功结果
        return {
            "success": True,
            "report_content": report_content,
            "response": formatted_response,
            "notice": "注意，先整理<report_content>，必须将上面这项<response>包含在整理后的<report_content>中",
            "well_info": {
                "well_name": well_data.get("wellName", ""),
                "well_type": well_data.get("wellType", ""),
                "total_depth": well_data.get("totalDepth_m", 0)
            },
            "archive_folder": timestamp_folder,
            "structure_image_path": structure_image_path,
            "info_image_path": info_image_path
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"生成井身结构图时发生未知错误: {str(e)}",
            "error_code": "UNKNOWN_ERROR",
            "details": str(e)
        }

def main():
    """主入口函数"""
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
