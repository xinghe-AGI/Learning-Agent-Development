# conda 常用命令

## 查看与创建环境

```powershell
# 查看已有环境，当前环境前会显示 *
conda env list

# 创建指定 Python 版本的环境
conda create -n agent-learning python=3.12
```

## 激活与退出环境

```powershell
conda activate agent-learning
conda deactivate
```

## 检查当前解释器

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -m pip --version
```

使用 `python -m pip` 可以减少“终端里的 pip 属于另一个 Python 环境”的混淆。

## 导出与恢复环境

```powershell
# 导出 Conda 环境定义
conda env export --from-history > environment.yml

# 根据文件创建环境
conda env create -f environment.yml
```

`--from-history` 只记录主动安装的主要依赖，更适合跨机器复现；如果需要完全锁定全部依赖，可以去掉该参数，但文件会更依赖当前平台。

## 删除环境

```powershell
conda deactivate
conda env remove -n agent-learning
```

删除前先运行 `conda env list`，确认环境名和路径，避免误删仍在使用的环境。

## 相关笔记

- [AI 应用开发环境搭建](<02-开发环境的搭建.md>)
- [LangChain 生态简介](<01-LangChain生态简介.md>)
