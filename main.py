"""
井身结构图生成器 MCP 服务

基于井数据生成井身结构图的服务
"""

import json
import subprocess
import os
import shutil
import time
import glob
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("awesome_well_MCP")


def get_package_data_dir() -> Path:
    """获取包数据目录路径"""
    return Path(__file__).parent


def get_generator_exe_path() -> Path:
    """获取生成器exe文件路径"""
    return get_package_data_dir() / "well_structure_generator.exe"


def get_templates_dir() -> Path:
    """获取模板文件目录路径"""
    return get_package_data_dir() / "templates"


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
        backup_path = Path("well_data_backup.json")
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
        generator_path = get_generator_exe_path()
        if not generator_path.exists():
            print(f"well_structure_generator.exe 不存在: {generator_path}")
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
        
        # 5. 检测成功后等待1秒，然后继续
        print("检测成功，等待1秒后继续...")
        time.sleep(1)
        
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
        png_files = ["well_structure_plot.png"]
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
            "deviationData_raw.csv"
        ]
        for filename in csv_files:
            source_file = Path(filename)
            if source_file.exists():
                target_file = target_folder / filename
                shutil.move(str(source_file), str(target_file))
                moved_files.append(filename)
                print(f"已移动CSV文件: {filename}")
        
        # 3. 移动JSON文件
        json_files = ["well_data.json"]
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
        png_file = "well_structure_plot.png"
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


def wait_for_png_generation(max_attempts: int = 10) -> bool:
    """检测PNG图片生成，每隔1秒检查一次"""
    try:
        print("开始检测PNG图片生成...")
        for attempt in range(max_attempts):
            png_files = glob.glob("*.png")
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


def wait_for_report_generation(max_attempts: int = 10) -> bool:
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


def format_simple_response(image_path: str) -> str:
    """简化的格式化回答"""
    try:
        response = f"井身结构示意图为：\n![PNG]({image_path})"
        return response
    except Exception as e:
        print(f"格式化回答失败: {e}")
        return ""


def cleanup_temp_files():
    """清理临时文件"""
    try:
        # 清理备份文件
        backup_path = Path("well_data_backup.json")
        if backup_path.exists():
            backup_path.unlink()
    except Exception as e:
        print(f"清理临时文件失败: {e}")


@mcp.tool()
def generate_well_structure(well_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成井身结构图
    
    Args:
        well_data: 井数据JSON对象（必需）
    
    Returns:
        包含生成结果和图片数据的字典
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
        image_path = f"{folder_absolute_path}\\well_structure_plot.png"
        
        # 清理临时文件
        cleanup_temp_files()
        
        # 格式化简化回答
        formatted_response = format_simple_response(image_path)
        
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
            "image_path": image_path
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
