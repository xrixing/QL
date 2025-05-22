#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
塔斯汀汉堡签到脚本
最后更新：2025-05-23
"""

import requests
import re
import os
import json
from datetime import datetime

# 初始化日志
print('============📣初始化📣============')
version = '1.46.8'
all_print_list = []

def myprint(msg):
    """打印并记录日志"""
    print(msg)
    all_print_list.append(f"{msg}\n")

def months_between_dates(d1):
    """计算两个日期之间的月份差"""
    d2 = datetime.today()
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    return (d2.year - d1.year) * 12 + d2.month - d1.month

def send_pushplus_notification(content):
    """发送PushPlus通知"""
    if 'PUSHPLUS_TOKEN' not in os.environ:
        myprint('未设置PUSHPLUS_TOKEN，跳过通知发送')
        return
    
    token = os.environ['PUSHPLUS_TOKEN']
    if not token:
        myprint('PUSHPLUS_TOKEN为空，跳过通知发送')
        return
    
    url = 'http://www.pushplus.plus/send'
    data = {
        'token': token,
        'title': '塔斯汀汉堡签到结果',
        'content': content,
        'template': 'txt'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                myprint('✅ PushPlus通知发送成功')
            else:
                myprint(f'❌ PushPlus通知发送失败: {result.get("msg", "未知错误")}')
        else:
            myprint(f'❌ PushPlus通知发送失败，状态码: {response.status_code}')
    except Exception as e:
        myprint(f'❌ 发送PushPlus通知异常: {str(e)}')

def get_activity_id(ck):
    """获取签到活动ID"""
    headers = {
        'user-token': ck, 
        'version': version, 
        'channel': '1',
        'Content-Type': 'application/json'
    }
    data = {
        "shopId": "",
        "birthday": "",
        "gender": 0,
        "nickName": None,
        "phone": ""
    }
    
    try:
        response = requests.post(
            'https://sss-web.tastientech.com/api/minic/shop/intelligence/banner/c/list',
            json=data,
            headers=headers,
            timeout=15
        )
        result = response.json()
        
        for item in result.get('result', []):
            if '签到' in item.get('bannerName', ''):
                try:
                    jump_data = json.loads(item.get('jumpPara', '{}'))
                    if 'activityId' in jump_data:
                        activity_id = jump_data['activityId']
                        myprint(f"🔍 获取到活动ID: {activity_id}")
                        return activity_id
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        myprint(f"❌ 获取活动ID出错: {str(e)}")
    
    # 默认计算方式
    base_id = 59
    base_date = "2025-05-01"
    calculated_id = base_id + months_between_dates(base_date)
    myprint(f"🔢 使用计算的活动ID: {calculated_id}")
    return calculated_id

def do_sign_in(ck):
    """执行签到操作"""
    activity_id = get_activity_id(ck)
    headers = {
        'user-token': ck,
        'version': version,
        'channel': '1',
        'Content-Type': 'application/json'
    }
    
    try:
        # 获取用户信息
        user_info = requests.get(
            'https://sss-web.tastientech.com/api/intelligence/member/getMemberDetail',
            headers=headers,
            timeout=15
        ).json()
        
        if user_info.get('code') != 200:
            myprint(f"❌ 登录失败: {user_info.get('msg', '未知错误')}")
            return
        
        phone = user_info.get('result', {}).get('phone', '未知号码')
        myprint(f"📱 账号: {phone}")
        
        # 执行签到
        sign_data = {
            "activityId": activity_id,
            "memberName": "",
            "memberPhone": phone
        }
        sign_result = requests.post(
            'https://sss-web.tastientech.com/api/sign/member/signV2',
            json=sign_data,
            headers=headers,
            timeout=15
        ).json()
        
        if sign_result.get('code') == 200:
            reward = sign_result.get('result', {}).get('rewardInfoList', [{}])[0]
            if reward.get('rewardName'):
                myprint(f"🎉 签到成功！获得: {reward['rewardName']}")
            else:
                myprint(f"🎉 签到成功！获得: {reward.get('point', '未知')}积分")
        else:
            myprint(f"❌ 签到失败: {sign_result.get('msg', '未知错误')}")
            
    except Exception as e:
        myprint(f"❌ 签到过程出错: {str(e)}")

def main():
    """主函数"""
    # 获取账号列表
    if 'tsthbck' in os.environ:
        accounts = re.split("@|&", os.environ.get("tsthbck"))
        myprint(f"📊 找到 {len(accounts)} 个账号")
    else:
        myprint("⚠️ 未找到tsthbck环境变量")
        return
    
    # 处理每个账号
    for idx, account in enumerate(accounts, 1):
        if not account.strip():
            continue
            
        myprint(f"\n🔔 处理第 {idx} 个账号")
        myprint("----------------------")
        do_sign_in(account.strip())
        myprint("----------------------")

if __name__ == '__main__':
    try:
        myprint("\n🟢 开始执行签到任务")
        main()
        myprint("\n🟢 任务执行完成")
        
        # 发送通知
        notification_content = ''.join(all_print_list)
        send_pushplus_notification(notification_content)
        
    except Exception as e:
        myprint(f"\n❌ 程序运行出错: {str(e)}")
    finally:
        myprint("\n⏱️ 脚本执行结束")
