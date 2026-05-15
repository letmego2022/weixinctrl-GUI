@echo off
chcp 65001 >nul 2>&1
cd /d "C:\Users\Administrator\Desktop\个人"
claude -p --dangerously-skip-permissions "read plan_knowledge.md in the current directory, then execute the TODO list step by step. 直接打印执行结果文字，不需要确认。"
