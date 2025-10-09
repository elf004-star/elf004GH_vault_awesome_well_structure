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
                import awesome_well_mcp
                package_dir = Path(awesome_well_mcp.__file__).parent
                generator_path = package_dir / "WellStructure.exe"
                if not generator_path.exists():
                    print("WellStructure.exe 不存在")
                    return False
            except ImportError:
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
    """
    生成井身结构图
    
    Args:
        well_data: 井数据JSON对象（必需）。
        JSON对象中 `wellName` 和 `totalDepth_m` 分别定义井的名字和深度。`wellType` 和 `deviationData` 是定义井眼轨迹形态的核心配置项。`wellType` 为必填项，用于设置井的类型，可选值为 `straight well` (直井)、`deviated well` (定向井) 或 `horizontal well` (水平井)。`deviationData` 配置块仅在井型不为直井时生效，用于定义井身的具体几何参数。其中 `kickoffPoint_m` 是绘图采用的作图采用造斜点，而 `REAL_kickoffPoint_m` 是在示意图上向用户显示的造斜点，若无特殊要求两者一致即可；`targetPointA_m` 和 `targetPointA_verticalDepth_m` 分别设置A靶点的井深和垂深；`targetPointB_m` 设置B靶点的井深；`deviationAngle_deg` 设置井斜角；`DistanceAB_m` 设置A靶点到B靶点的直线距离。尽管部分数据缺失时服务端会生成默认值，但仍建议优先设置 `REAL_kickoffPoint_m`、`targetPointA_verticalDepth_m`、`targetPointA_m`、`targetPointB_m` 和 `deviationAngle_deg`。\n\n**配置示例：**\n\n```json\n"wellName": "资101井",\n"totalDepth_m": 6900,\n"wellType": "deviated well",\n  "deviationData": {\n    "kickoffPoint_m": 3060,\n    "deviationAngle_deg": 30,\n    "targetPointA_m": 5090,\n    "targetPointA_verticalDepth_m": 4825,\n    "targetPointB_m": 6890,\n    "DistanceAB_m": 1800,\n    "REAL_kickoffPoint_m": 3060\n  }\n```\n\n上述配置定义了一口定向井，井名为资101井，井深6900米，其显示的造斜点为3060米，A靶点的垂深为4825米、井深为5090米，B靶点的井深为6890米，A、B两靶点间的距离为1800米。
        JSON对象中`stratigraphy` 配置项用于定义井眼剖面图中的地层分层信息。它是一个对象数组，每个对象代表一个独立的地层，通过 `name` 指定地层名称，`topDepth_m` 和 `bottomDepth_m` 分别定义其顶、底深度（垂深，单位：米）。一个关键的约束是，为保证数据连续性，上一地层的 `bottomDepth_m` 必须与下一地层的 `topDepth_m` 完全一致，否则将导致数据验证失败，服务端会拒绝执行任务。\n\n**配置示例：**\n\n```json\n"stratigraphy": [\n    {"name": "遂宁组", "topDepth_m": 0, "bottomDepth_m": 150},\n    {"name": "沙溪庙组", "topDepth_m": 150, "bottomDepth_m": 1112},\n    {"name": "凉高山组", "topDepth_m": 1112, "bottomDepth_m": 1248}\n  ]\n```\n\n上述配置定义了三个连续的地层：遂宁组（0-150米）、沙溪庙组（150-1112米）和凉高山组（1112-1248米）。
        JSON对象中`drillingFluidAndPressure` 配置项用于定义沿井深的钻井液密度设计和压力剖面。该配置为一个对象数组，其中每个对象代表一个深度区间。在每个区间内，`topDepth_m` 和 `bottomDepth_m` 分别设置区间的顶、底深度；`porePressure_gcm3` 设置该区间的孔隙压力当量密度（单位：g/cm³）；`pressureWindow_gcm3` 则通过 `min` 和 `max` 子属性定义了该区间的安全钻井液密度窗口。与地层配置类似，该项也必须保证数据的连续性，即上一区间的 `bottomDepth_m` 必须与下一区间的 `topDepth_m` 完全一致。\n\n**配置示例：**\n\n```json\n"drillingFluidAndPressure": [\n    {"topDepth_m": 0, "bottomDepth_m": 150, "porePressure_gcm3": 1.085, "pressureWindow_gcm3": {"min": 1.05, "max": 1.10}},\n    {"topDepth_m": 150, "bottomDepth_m": 1195, "porePressure_gcm3": 1.085, "pressureWindow_gcm3": {"min": 1.40, "max": 1.55}},\n    {"topDepth_m": 1195, "bottomDepth_m": 1520, "porePressure_gcm3": 1.32, "pressureWindow_gcm3": {"min": 1.40, "max": 1.55}}\n  ]\n```\n\n上述配置定义了三个连续的钻井液设计区间：\n*   **0 - 150米**：孔隙压力当量密度为 1.085 g/cm³，安全密度窗口为 1.05 - 1.10 g/cm³。\n*   **150 - 1195米**：孔隙压力当量密度为 1.085 g/cm³，安全密度窗口为 1.40 - 1.55 g/cm³。\n*   **1195 - 1520米**：孔隙压力当量密度为 1.32 g/cm³，安全密度窗口为 1.40 - 1.55 g/cm³。
        JSON对象中`wellboreStructure` 配置项用于定义井身的物理结构，它包含两个核心部分：`holeSections`（裸眼井段）和 `casingSections`（套管程序）。\n\n*   `holeSections` 是一个对象数组，用于描述各开次钻进的裸眼井段。每个对象通过 `topDepth_m` 和 `bottomDepth_m` 定义井段的顶、底深度，即从 `topDepth_m` 开始到 `bottomDepth_m`结束，`diameter_mm` 指定该井段的钻头直径（单位：毫米），而可选配置项 `note_in` 则用于补充说明（如井眼尺寸的英寸单位）。\n*   `casingSections` 同样是一个对象数组，用于描述下入井中的各层套管。每个对象通过 `topDepth_m` 和 `bottomDepth_m` 定义套管的悬挂点和套管鞋深度，`od_mm` 指定套管的外径（单位：毫米），`note_in` 用于文字备注。通常，每一级套管的外径都应小于其对应井段的直径。\n\n**配置示例：**\n\n```json\n\"wellboreStructure\": {\n    \"holeSections\": [\n      {\"topDepth_m\": 0, \"bottomDepth_m\": 152, \"diameter_mm\": 660.4, \"note_in\": \"26\\\"\"},\n      {\"topDepth_m\": 152, \"bottomDepth_m\": 1498, \"diameter_mm\": 406.4, \"note_in\": \"Φ406.4mm\"},\n      {\"topDepth_m\": 1498, \"bottomDepth_m\": 4321, \"diameter_mm\": 311.2, \"note_in\": \"Φ311.2mm\"},\n      {\"topDepth_m\": 4321, \"bottomDepth_m\": 6950, \"diameter_mm\": 215.9, \"note_in\": \"Φ215.9mm\"}\n    ],\n    \"casingSections\": [\n      {\"topDepth_m\": 0, \"bottomDepth_m\": 150.62, \"od_mm\": 508, \"note_in\": \"20\\\"导管\"},\n      {\"topDepth_m\": 0, \"bottomDepth_m\": 1495.48, \"od_mm\": 346.08, \"note_in\": \"Φ346.08mm+339.72mm\"},\n      {\"topDepth_m\": 0, \"bottomDepth_m\": 4318.86, \"od_mm\": 247.65, \"note_in\": \"Φ247.65mm+Φ244.5mm\"},\n      {\"topDepth_m\": 0, \"bottomDepth_m\": 6945.83, \"od_mm\": 139.7, \"note_in\": \"Φ139.7mm油层套管\"}\n    ]\n}\n```\n\n上述配置详细定义了井身结构。`holeSections` 部分描述了从 660.4mm 表层井眼到 Φ215.9mm 生产井眼共四级钻井井段。`casingSections` 部分则对应地描述了下入的四层套管，包括 508mm 导管、技术套管及最后的油层套管。
        JSON对象中`legendConfig` 配置项用于自定义井眼轨迹示意图的图例和样式。可以通过 `casingLegend`、`holeLegend`、`kickoffLegend` 和 `targetPointsLegend` 这几个选项，分别控制是否在绘图时显示套管、井筒、造斜点和靶点的说明。此外，`fill` 选项控制是否对套管与井筒之间的环空进行颜色填充，以直观地表示固井水泥；`simpleinfo` 选项控制是否采用简化的方式打印（输出为PNG图片）井身结构信息。\n\n**配置示例：**\n\n```json\n"legendConfig": {\n    "casingLegend": false,\n    "holeLegend": false,\n    "kickoffLegend": true,\n    "targetPointsLegend": true,\n    "fill": true,\n    "simpleinfo": false\n  }\n```\n\n上述配置将会在井身结构旁中显示造斜点和靶点的说明（图例说明），但隐藏套管和井筒的说明（备注说明），同时会对井筒与套管间的环空进行填充，打印出详细形式的井身结构信息（PNG）。
        JSON对象中`pilotHoleGuideLine` 配置项用于导眼井辅助线、侧钻点的显示设置。可以通过 `topDepth_m` 和 `bottomDepth_m` 分别设置辅助线的顶深和底深（单位：米），使用 `diameter_mm` 设置其尺寸（单位：毫米），（前三项用户没有具体要求不进行设置，服务端会自动配置）。`display` 选项控制该辅助线是否显示，`highlight` 选项决定其是否以更明显的样式（黑色虚线）突出显示。最后，`side_tracking` 选项用于将关联的图例样式从“造斜点”切换为“侧钻点”。\n\n**配置示例：**\n\n```json\n"pilotHoleGuideLine": {\n    "display": true,\n    "highlight": true,\n    "side_tracking": true\n  }\n```\n\n上述配置将显示一条从造斜点到井底、尺寸为默认毫米的导眼井辅助线，并以高亮的黑色虚线样式呈现，同时其关联图例将显示为侧钻点样式。注意要显示侧钻点，必须先将 `legendConfig` 中的 `kickoffLegend` 设置为true（显示）。
        
    Returns:
        包含生成结果和图片数据的字典，包含井身结构图片（PNG）文件路径、井身结构信息图片（PNG）文件路径的和详细生成过程信息等
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

