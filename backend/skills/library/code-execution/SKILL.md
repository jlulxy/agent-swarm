---
name: code-execution
description: Write, execute, and debug code in various programming languages. Use when implementing features, fixing bugs, running scripts, or validating code logic.
version: "1.0.0"
author: system
category: code
tags:
  - code
  - programming
  - execution
  - debugging
  - development
trigger_keywords:
  - 代码
  - 编程
  - 执行
  - code
  - programming
  - execute
  - run
  - debug
requires_packages:
  - python
display_name: 代码执行
icon: 💻
---

# Code Execution

编写、执行和调试各种编程语言的代码。适用于实现功能、修复bug、运行脚本或验证代码逻辑。

## Workflow

1. **理解需求**: 明确代码目标
   - 理解功能需求
   - 确定技术栈和限制
   - 识别输入输出

2. **设计方案**: 规划实现思路
   - 选择算法和数据结构
   - 设计代码结构
   - 考虑边界情况

3. **编写代码**: 实现功能
   - 遵循编码规范
   - 添加必要注释
   - 处理异常情况

4. **测试验证**: 确保正确性
   - 编写测试用例
   - 覆盖边界情况
   - 验证输出结果

5. **调试优化**: 修复和改进
   - 定位和修复bug
   - 优化性能
   - 重构代码

6. **文档说明**: 完善文档
   - 编写使用说明
   - 说明依赖和环境
   - 记录已知问题

## Coding Standards

### 代码质量原则

- **可读性**: 代码清晰易懂
- **可维护性**: 结构合理，易于修改
- **可测试性**: 便于编写测试
- **健壮性**: 妥善处理异常

### 命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| 变量 | snake_case | user_name |
| 函数 | snake_case | get_user_data() |
| 类名 | PascalCase | UserService |
| 常量 | UPPER_CASE | MAX_RETRY_COUNT |

### 注释规范

```python
def calculate_total(items: List[Item], discount: float = 0) -> float:
    """
    计算订单总金额
    
    Args:
        items: 商品列表
        discount: 折扣比例 (0-1)
    
    Returns:
        折扣后的总金额
    
    Raises:
        ValueError: 折扣值超出范围时抛出
    """
    pass
```

## Error Handling

### 异常处理原则

```python
# 好的实践
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    handle_specific_error(e)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise  # 重新抛出未预期的异常
finally:
    cleanup()

# 避免
try:
    result = risky_operation()
except:  # 不要捕获所有异常
    pass  # 不要忽略异常
```

## Guidelines

- 遵循语言的编码规范
- 优先使用标准库
- 避免过度设计
- 代码应该自文档化
- 及时处理技术债务

## Examples

```python
# 需求: 实现一个带重试的 HTTP 请求函数

import time
from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException

def fetch_with_retry(
    url: str,
    max_retries: int = 3,
    timeout: float = 10,
    backoff_factor: float = 0.5
) -> Optional[Dict[str, Any]]:
    """
    带重试机制的 HTTP GET 请求
    
    Args:
        url: 请求 URL
        max_retries: 最大重试次数
        timeout: 请求超时时间（秒）
        backoff_factor: 重试间隔因子
    
    Returns:
        JSON 响应数据，失败返回 None
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if attempt == max_retries - 1:
                print(f"All retries failed: {e}")
                return None
            
            wait_time = backoff_factor * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
            time.sleep(wait_time)
    
    return None

# 使用示例
if __name__ == "__main__":
    data = fetch_with_retry("https://api.example.com/data")
    if data:
        print(f"Success: {data}")
```

## Debugging Workflow

1. **复现问题**: 确定稳定的复现步骤
2. **定位范围**: 通过日志/断点缩小范围
3. **分析原因**: 理解错误的根本原因
4. **修复验证**: 修复后验证所有相关场景
5. **防止复发**: 添加测试防止回归

## Safety Checks

- 不执行未经审查的代码
- 注意资源清理（文件、连接）
- 避免硬编码敏感信息
- 验证外部输入

## Success Criteria

- 代码功能正确
- 通过所有测试用例
- 性能满足要求
- 代码可读性好
- 异常处理完善
