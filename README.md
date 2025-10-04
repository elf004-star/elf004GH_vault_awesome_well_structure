# 井身结构图生成器 MCP 服务

这是一个基于 MCP (Model Context Protocol) 的井身结构图生成服务，可以根据井数据自动生成井身结构图。

## 功能特性

- 支持三种基本井型：直井、水平井、定向井，支持直改平和侧钻井转换
- 自动生成井身结构图（PNG格式）
- 生成相关数据文件（CSV格式）
- 返回简化的图片路径（大幅减少token消耗，仅支持path格式）
- 自动文件归档管理（时间戳文件夹）
- 完整的错误处理和验证

## 使用方法

### 启动MCP服务

```bash
# 使用uv运行（推荐）
uv run python main.py

# 或直接使用python
python main.py
```

### MCP客户端配置

在MCP客户端中添加以下配置：

```json
{
  "mcpServers": {
    "well-structure-generator": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "项目路径"
    }
  }
}
```

### MCP工具调用

工具名称：`generate_well_structure`

参数：
- `well_data`: 井数据JSON对象（必需）

返回：
- 成功时返回简化的图片路径（<1200 token，仅支持path格式）
- 失败时返回错误信息

**返回格式**：
```
井身结构示意图为：
![PNG](文件夹绝对路径+well_structure_plot.png)
```

**返回数据结构**：
```json
{
  "success": true,
  "response": "井身结构示意图为：\n![PNG](图片绝对路径)",
  "notice": "注意，必须将上面这项<response>包含在最终回答中",
  "well_info": {
    "well_name": "井名",
    "well_type": "井型", 
    "total_depth": 深度
  },
  "archive_folder": "2025-10-03_11-37-29",
  "image_path": "图片的绝对路径"
}
```

**Token优化**：
- 返回内容大幅简化，减少token消耗
- 每次返回不超过1200个token
- 移除冗长的报告内容，只保留核心信息

### 支持的井型

#### 基本井型定义

1. **直井** (`straight well`)
   - `deviationAngle_deg: 0`
   - `kickoffPoint_m: null`
   - `targetPointA_m: null`
   - `targetPointB_m: null`
   - `DistanceAB_m: null`

2. **定向井** (`deviated well`)
   - `deviationAngle_deg: 0 < 角度 < 90`
   - `kickoffPoint_m: 有值`（造斜点深度（可根据作图情况调整））
   - `targetPointA_m: 有值`（目标点A井深）
   - `targetPointA_verticalDepth_m: 有值`（目标点A的垂深）,
   - `targetPointB_m: 有值`（目标点B井深）
   - `DistanceAB_m: 有值`（AB点间距离）
   - `REAL_kickoffPoint_m: 有值`（实际造斜点）

3. **水平井** (`horizontal well`)
   - `deviationAngle_deg: 90`
   - `kickoffPoint_m: 有值`（造斜点深度（可根据作图情况调整））
   - `targetPointA_m: 有值`（目标点A井深）
   - `targetPointA_verticalDepth_m: 有值`（目标点A的垂深）,
   - `targetPointB_m: 有值`（目标点B井深）
   - `DistanceAB_m: 有值`（AB点间距离）
   - `REAL_kickoffPoint_m: 有值`（实际造斜点）

#### 井型转换规则

当 `wellType` 为 `horizontal well` 或 `deviated well` 时，如果配置了 `pilotHoleGuideLine` 并设置 `"side_tracking": true`，则可以表示：

- **直改平井**：从直井段开始，在指定深度开始造斜
- **侧钻井**：从现有井眼侧向钻出新的井眼

#### pilotHoleGuideLine 配置示例

```json
"pilotHoleGuideLine": {
  "topDepth_m": 4530,        // 导眼井段起始深度
  "bottomDepth_m": 5150,      // 导眼井段结束深度
  "diameter_mm": 215.9,       // 导眼井段直径
  "display": true,            // 是否显示导眼井段
  "highlight": true,          // 是否高亮显示
  "side_tracking": true       // 是否为侧钻井
}
```

#### legendConfig 图例配置示例

```json
"legendConfig": {
  "casingLegend": true,        // 是否显示套管图例
  "holeLegend": false,         // 是否显示井眼图例
  "kickoffLegend": true,       // 是否显示造斜点图例
  "targetPointsLegend": true   // 是否显示目标点图例
}
```

## 生成的文件

每次请求完成后，所有生成的文件会自动移动到以时间戳命名的文件夹中：

- `well_structure_plot.png`: 井身结构图
- `well_structure_report.md`: 井身结构报告
- `stratigraphy.csv`: 地层数据
- `casing_sections.csv`: 套管数据
- `hole_sections.csv`: 井眼数据
- `drilling_fluid_pressure.csv`: 钻井液压力数据
- `deviationData.csv`: 偏移数据
- 对应的 `*_raw.csv` 原始数据文件

**文件归档**：
- 文件夹命名格式：`YYYY-MM-DD_HH-MM-SS`
- 示例：`2025-10-03_11-37-29`
- 每次请求都会创建新的归档文件夹

## 技术实现

- 使用 FastMCP 框架
- 支持异步处理
- 完整的错误处理机制
- 自动文件备份和清理
- 3秒延迟确保程序完全结束
- Token优化，减少API调用成本

## 模板文件

项目提供了四种井型的设计模板，位于 `templates/` 目录：

- `well_data（导眼井）.json` - 直井设计模板
- `well_data（导向井） .json` - 定向井设计模板  
- `well_data（水平井）.json` - 水平井设计模板
- `well_data（直改平）.json` - 直改平井设计模板

这些模板文件展示了不同井型的标准数据结构和参数配置，可以作为设计新井的参考。

## 数据结构设计要求

### stratigraphy（地层数据）

地层数据定义了井眼穿过的各个地质层位信息：

```json
"stratigraphy": [
  {
    "name": "遂宁组",           // 地层名称
    "topDepth_m": 0,           // 地层顶深（米）
    "bottomDepth_m": 45        // 地层底深（米）
  },
  {
    "name": "沙溪庙组",
    "topDepth_m": 45,
    "bottomDepth_m": 1195
  }
  // ... 更多地层
]
```

**设计要求：**
- 地层必须按深度顺序排列，从浅到深
- 相邻地层的深度必须连续（上一个地层的底深 = 下一个地层的顶深）
- 最后一个地层的底深应等于或接近 `totalDepth_m`
- 地层名称使用标准地质术语

### drillingFluidAndPressure（钻井液压力数据）

钻井液压力数据定义了不同深度段的压力参数：

```json
"drillingFluidAndPressure": [
  {
    "topDepth_m": 0,                    // 压力段顶深（米）
    "bottomDepth_m": 50,                 // 压力段底深（米）
    "porePressure_gcm3": 1.00,          // 孔隙压力（g/cm³）
    "pressureWindow_gcm3": {             // 压力窗口
      "min": 1.05,                       // 最小压力（g/cm³）
      "max": 1.10                        // 最大压力（g/cm³）
    }
  }
  // ... 更多压力段
]
```

**设计要求：**
- 压力段必须按深度顺序排列，从浅到深
- 相邻压力段的深度必须连续
- 孔隙压力值应在地质上合理
- 压力窗口的最小值应大于孔隙压力
- 压力段数量通常少于地层数量，可以合并相似压力特征的地层

### wellboreStructure（井身结构）

井身结构定义了井眼和套管的几何参数：

```json
"wellboreStructure": {
  "holeSections": [                     // 井眼段
    {
      "topDepth_m": 0,                  // 井眼段顶深（米）
      "bottomDepth_m": 50,               // 井眼段底深（米）
      "diameter_mm": 660.4,             // 井眼直径（毫米）
      "note_in": "26\""                  // 备注（英寸）
    }
    // ... 更多井眼段
  ],
  "casingSections": [                   // 套管段
    {
      "topDepth_m": 0,                  // 套管顶深（米）
      "bottomDepth_m": 50,               // 套管底深（米）
      "od_mm": 508,                      // 套管外径（毫米）
      "note_in": "20\""                  // 备注（英寸）
    }
    // ... 更多套管段
  ],
  "pilotHoleGuideLine": {               // 导眼井段（可选）
    "topDepth_m": 4530,                 // 导眼井段顶深（米）
    "bottomDepth_m": 5150,              // 导眼井段底深（米）
    "diameter_mm": 215.9,               // 导眼井段直径（毫米）
    "display": true,                    // 是否显示
    "highlight": true,                  // 是否高亮
    "side_tracking": true               // 是否为侧钻井
  }
}
```

**设计要求：**

#### holeSections（井眼段）
- 井眼段必须按深度顺序排列，从浅到深
- 相邻井眼段的深度必须连续
- 井眼直径通常从上到下递减
- 最后一个井眼段的底深应等于 `totalDepth_m`

#### casingSections（套管段）
- 套管段必须按深度顺序排列，从浅到深
- 套管顶深通常为0（从井口开始）
- 当套管顶深不为0，会给顶深增加一个悬挂器
- 套管外径通常从上到下递减
- 套管底深应小于等于对应井眼段的底深

#### pilotHoleGuideLine（导眼井段）
- 仅在直改平井或侧钻井中使用
- `topDepth_m` 和 `bottomDepth_m` 定义导眼井段范围
- `diameter_mm` 应与对应井眼段直径一致
- `side_tracking: true` 表示侧钻井特征
