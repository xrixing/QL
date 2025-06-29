# -*- coding: utf-8 -*
'''
定时自定义
0 0 1 * * ? iKuuu.py
new Env('iKuuu签到');
'''
import requests
import re
import json
import os
import datetime
import urllib.parse
import sys
import time
from bs4 import BeautifulSoup

# 添加青龙脚本根目录到Python路径
QL_SCRIPTS_DIR = '/ql/scripts'  # 青龙脚本默认目录
sys.path.append(QL_SCRIPTS_DIR)

# 添加notify可能存在的其他路径
POSSIBLE_PATHS = [
    '/ql',                      # 青龙根目录
    '/ql/data/scripts',         # 新版青龙数据目录
    '/ql/scripts/notify',       # 自定义通知目录
    os.path.dirname(__file__)   # 当前脚本目录
]

for path in POSSIBLE_PATHS:
    if os.path.exists(os.path.join(path, 'notify.py')):
        sys.path.append(path)
        break

try:
    from notify import send
except ImportError:
    print("⚠️ 无法加载通知模块，请检查路径配置")
    send = lambda title, content: None  # 创建空函数防止报错

# 初始域名
ikun_host = "ikuuu.one"  # 自动更新于2025-04-29 13:08:20
backup_hosts = ["ikuuu.one", "ikuuu.pw", "ikuuu.me"]  # 备用域名列表

def get_latest_ikun_host():
    test_url = f"https://{ikun_host}/"
    try:
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            if "官网域名已更改" in response.text or "Domain deprecated" in response.text:
                print("检测到域名变更通知，正在提取新域名...")
                h2_matches = re.findall(r'<h2>.*?(?:域名|domain)[：:]\s*([a-zA-Z0-9.-]+)</h2>', response.text)
                if h2_matches:
                    return h2_matches[0]
                js_matches = re.findall(r'https?://([a-zA-Z0-9.-]+)/auth/login', response.text)
                if js_matches:
                    return js_matches[0]
                fallback_match = re.search(r'(?:域名|domain)[：:]\s*([a-zA-Z0-9.-]+)', response.text)
                if fallback_match:
                    return fallback_match.group(1)
                print("⚠️ 检测到域名变更但无法提取新域名")
                return None
            else:
                print("✅ 当前域名正常")
                return None
    except Exception as e:
        print(f"域名检测异常: {e}")
    return None

def update_self_host(new_host):
    script_path = os.path.abspath(__file__)
    with open(script_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("ikun_host = "):
            lines[i] = f'ikun_host = "{new_host}"  # 自动更新于{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            updated = True
            break
    if updated:
        with open(script_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 脚本已更新至域名: {new_host}")
        return True
    else:
        print("⚠️ 域名更新失败")
        return False

def test_host_reachable(host):
    try:
        response = requests.get(f"https://{host}/", timeout=10)
        return response.status_code == 200
    except:
        return False

def get_remaining_flow(cookies):
    """获取用户剩余流量信息"""
    user_url = f'https://{ikun_host}/user'
    try:
        # 获取用户页面
        user_page = requests.get(user_url, cookies=cookies, timeout=15)
        if user_page.status_code != 200:
            return "获取流量失败", "状态码: " + str(user_page.status_code)
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(user_page.text, 'html.parser')
        
        # 查找包含剩余流量的卡片
        flow_cards = soup.find_all('div', class_='card card-statistic-2')
        for card in flow_cards:
            h4_tag = card.find('h4')
            if h4_tag and '剩余流量' in h4_tag.text:
                # 查找流量数值
                counter_span = card.find('span', class_='counter')
                if counter_span:
                    flow_value = counter_span.text.strip()
                    
                    # 查找流量单位
                    unit_text = ""
                    next_sibling = counter_span.next_sibling
                    if next_sibling:
                        unit_text = next_sibling.strip()
                    
                    return flow_value, unit_text
        
        # 如果没有找到，尝试其他方式
        flow_div = soup.find('div', string='剩余流量')
        if flow_div:
            parent_div = flow_div.find_parent('div', class_='card-body')
            if parent_div:
                flow_text = parent_div.get_text(strip=True).replace('剩余流量', '')
                return flow_text.split()[0], flow_text.split()[1] if len(flow_text.split()) > 1 else ""
        
        return "未找到", "流量信息"
        
    except Exception as e:
        return "流量获取异常", str(e)

def ikuuu_signin(email, password):
    params = {'email': email, 'passwd': password, 'code': ''}
    login_url = f'https://{ikun_host}/auth/login'
    try:
        # 登录请求
        login_res = requests.post(login_url, data=params, timeout=15)
        if login_res.status_code != 200:
            flow_value, flow_unit = "登录失败", "无法获取"
            return False, f"登录失败（状态码{login_res.status_code}）", flow_value, flow_unit
        
        login_data = login_res.json()
        if login_data.get('ret') != 1:
            flow_value, flow_unit = "登录失败", "无法获取"
            return False, f"登录失败：{login_data.get('msg', '未知错误')}", flow_value, flow_unit
        
        # 获取用户剩余流量
        cookies = login_res.cookies
        flow_value, flow_unit = get_remaining_flow(cookies)
        
        # 执行签到
        checkin_res = requests.post(f'https://{ikun_host}/user/checkin', cookies=cookies, timeout=15)
        if checkin_res.status_code != 200:
            return False, f"签到失败（状态码{checkin_res.status_code}）", flow_value, flow_unit
        
        checkin_data = checkin_res.json()
        if checkin_data.get('ret') == 1:
            return True, f"成功 | {checkin_data.get('msg', '')}", flow_value, flow_unit
        else:
            return False, f"签到失败：{checkin_data.get('msg', '未知错误')}", flow_value, flow_unit
    except json.JSONDecodeError:
        return False, "响应解析失败", "未知", "未知"
    except requests.exceptions.Timeout:
        return False, "请求超时", "未知", "未知"
    except Exception as e:
        return False, f"请求异常：{str(e)}", "未知", "未知"

def send_qinglong_notification(results):
    """
    使用青龙面板内置通知系统发送通知
    需要青龙面板已配置通知渠道（如钉钉、企业微信等）
    """
    title = "iKuuu签到通知"
    
    # 构建消息内容
    success_count = sum(1 for res in results if res['success'])
    failure_count = len(results) - success_count
    
    message = [
        f"🔔 签到完成 | 成功：{success_count} 失败：{failure_count}",
        "================================"
    ]
    
    for index, res in enumerate(results, 1):
        status = "✅ 成功" if res['success'] else "❌ 失败"
        message.append(f"{index}. {res['email']}")
        message.append(f"  状态：{status}")
        message.append(f"  详情：{res['message']}")
        message.append(f"  剩余流量：{res['flow_value']} {res['flow_unit']}")
        message.append("--------------------------------")
    
    # 添加统计信息
    message.append("\n🕒 执行时间：" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        # 发送通知（青龙自动处理多通知渠道）
        send(title, "\n".join(message))
        print("✅ 通知已发送")
    except Exception as e:
        print(f"⚠️ 通知发送失败，请检查通知配置: {str(e)}")

if __name__ == "__main__":
    # ==================== 域名更新逻辑 ====================
    print(f"当前域名: {ikun_host}")
    latest_host = get_latest_ikun_host()
    if latest_host:
        print(f"检测到新域名: {latest_host}")
        if update_self_host(latest_host):
            ikun_host = latest_host
    
    # ==================== 域名可用性检查 ====================
    if not test_host_reachable(ikun_host):
        print("主域名不可用，尝试备用域名...")
        found = False
        for host in backup_hosts:
            if test_host_reachable(host):
                ikun_host = host
                print(f"切换到备用域名: {ikun_host}")
                found = True
                break
        if not found:
            print("❌ 所有域名均不可用")
            exit(1)
    
    # ==================== 账户处理 ====================
    accounts = []
    account_str = os.getenv('IKUUU_ACCOUNTS')
    if not account_str:
        print("❌ 未找到环境变量 IKUUU_ACCOUNTS")
        exit(1)
    
    for line in account_str.strip().splitlines():
        if ':' in line:
            email, pwd = line.split(':', 1)
            accounts.append((email.strip(), pwd.strip()))
        else:
            print(f"⚠️ 忽略无效账户行: {line}")
    
    if not accounts:
        print("❌ 未找到有效账户")
        exit(1)
    
    # ==================== 执行签到 ====================
    results = []
    for email, pwd in accounts:
        print(f"\n处理账户: {email}")
        success, msg, flow_value, flow_unit = ikuuu_signin(email, pwd)
        results.append({
            'email': email, 
            'success': success, 
            'message': msg,
            'flow_value': flow_value,
            'flow_unit': flow_unit
        })
        print(f"结果: {'成功' if success else '失败'} - {msg}")
        print(f"剩余流量: {flow_value} {flow_unit}")
        
        # 账户间延迟防止请求过快
        time.sleep(1)
    
    # ==================== 结果通知 ====================
    print("\n正在发送通知...")
    send_qinglong_notification(results)
    
    # ==================== 本地结果输出 ====================
    print("\n签到结果汇总:")
    for res in results:
        print(f"邮箱: {res['email']}")
        print(f"状态: {'成功' if res['success'] else '失败'}")
        print(f"详情: {res['message']}")
        print(f"剩余流量: {res['flow_value']} {res['flow_unit']}\n{'-'*40}")
