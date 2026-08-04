"""
将 ai_tc_cases 表中的用例数据改为有质量问题的版本，便于测试 AI 审核功能。
审核维度：name / summary / preconditions / test_data / topo / steps

用法：
  python degrade_cases.py          # 改造数据
  python degrade_cases.py restore  # 恢复到原始数据（原始数据保存在 degrade_cases_backup.json）
"""
import json
import os
import sys
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 15432,
    "user": "youlai",
    "password": "Youlai@2026",
    "dbname": "youlai_admin",
}

BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "degrade_cases_backup.json")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def backup_cases():
    """备份当前用例数据"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, summary, preconditions, topo, test_data, steps, review_status "
        "FROM ai_tc_cases WHERE is_deleted = 0 ORDER BY id"
    )
    rows = cur.fetchall()
    backup = []
    for r in rows:
        backup.append({
            "id": r[0],
            "name": r[1],
            "summary": r[2],
            "preconditions": r[3],
            "topo": r[4],
            "test_data": r[5],
            "steps": json.loads(r[6]) if isinstance(r[6], str) else r[6],
            "review_status": r[7],
        })
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    cur.close()
    conn.close()
    print(f"已备份 {len(backup)} 条用例到 {BACKUP_FILE}")
    return backup


def restore_cases():
    """从备份恢复"""
    if not os.path.exists(BACKUP_FILE):
        print(f"备份文件 {BACKUP_FILE} 不存在")
        sys.exit(1)
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        backup = json.load(f)

    conn = get_conn()
    cur = conn.cursor()
    for case in backup:
        cur.execute(
            """UPDATE ai_tc_cases 
               SET name=%s, summary=%s, preconditions=%s, topo=%s, 
                   test_data=%s, steps=%s, review_status=%s, update_time=NOW()
               WHERE id=%s""",
            (
                case["name"],
                case["summary"],
                case["preconditions"],
                case["topo"],
                case["test_data"],
                json.dumps(case["steps"], ensure_ascii=False),
                case["review_status"],
                case["id"],
            ),
        )
    conn.commit()
    cur.close()
    conn.close()
    print(f"已恢复 {len(backup)} 条用例")


def degrade_cases():
    """引入各种质量问题"""
    # 先备份
    backup_cases()

    conn = get_conn()
    cur = conn.cursor()

    # 读取当前所有用例
    cur.execute(
        "SELECT id, name, summary, preconditions, topo, test_data, steps FROM ai_tc_cases WHERE is_deleted=0 ORDER BY id"
    )
    rows = cur.fetchall()

    updates = []

    for r in rows:
        case_id = r[0]
        name = r[1]
        summary = r[2]
        preconditions = r[3]
        topo = r[4]
        test_data = r[5]
        steps = r[6] if isinstance(r[6], str) else json.dumps(r[6], ensure_ascii=False)

        # ---- 对不同用例引入不同类型的问题 ----

        # WAN-001 (id=1): 用例名称过长 + 测试思想过于简单 + 测试数据缺失
        if case_id == 1:
            name = "路由器PPPoE拨号连接建立及断开与重连测试验证长时间运行稳定性场景"
            summary = "测试拨号"
            test_data = ""

        # WAN-002 (id=2): 前置条件过于简略 + topo 缺失 + 步骤 expected 不明确
        elif case_id == 2:
            preconditions = "WAN口已连接"
            topo = ""
            steps = steps.replace('"expected":"配置界面正常"', '"expected":"OK"')
            steps = steps.replace('"expected":"WAN口成功获取IP地址、网关、DNS"', '"expected":"成功了"')

        # WAN-003 (id=3): summary 只重复 name + test_data 格式不规范
        elif case_id == 3:
            summary = "静态IP上网配置测试"
            test_data = "IP地址相关参数"

        # WAN-004 (id=4): 步骤逻辑紊乱，步骤顺序打乱
        elif case_id == 4:
            orig_steps = json.loads(steps)
            if len(orig_steps) >= 5:
                # 交换步骤 2 和 4，造成逻辑不合理
                orig_steps[1], orig_steps[3] = orig_steps[3], orig_steps[1]
                steps = json.dumps(orig_steps, ensure_ascii=False)

        # WAN-005 (id=5): 前置条件不完整 + 步骤 action 过于简略
        elif case_id == 5:
            preconditions = "WAN口已连接"
            steps = steps.replace('"action":"进入WAN口高级设置，找到MTU配置项"', '"action":"改MTU"')
            steps = steps.replace('"action":"将MTU值修改为1480"', '"action":"改值"')

        # WAN-006 (id=6): test_data 为空 + topo 过于简单
        elif case_id == 6:
            test_data = ""
            topo = "Router -> Internet"

        # WAN-007 (id=7): summary 含义模糊 + preconditions 缺失关键信息
        elif case_id == 7:
            summary = "测试端口的速率配置"
            preconditions = "设备正常运行"

        # WAN-008 (id=8): name 不够精确 + 步骤缺少 expected
        elif case_id == 8:
            name = "多WAN口测试"
            # 移除部分 expected
            orig_steps = json.loads(steps)
            for s in orig_steps:
                if s["step_no"] in [2, 5]:
                    s["expected"] = ""
            steps = json.dumps(orig_steps, ensure_ascii=False)

        # WAN-009 (id=9): preconditions 为空
        elif case_id == 9:
            preconditions = ""

        # WAN-010 (id=10): topo 缺失 + summary 质量低
        elif case_id == 10:
            topo = ""
            summary = "测试NAT和端口映射"

        # LAN-001 (id=11): name 过长 + 步骤 action/expected 含糊
        elif case_id == 11:
            name = "验证LAN口DHCP服务器能否正确地为下联设备分配IP地址及DNS网关信息"
            orig_steps = json.loads(steps)
            for s in orig_steps:
                if s["step_no"] in [3, 5]:
                    s["expected"] = "应该可以"
            steps = json.dumps(orig_steps, ensure_ascii=False)

        # LAN-002 (id=12): summary 太简单 + test_data 不明确
        elif case_id == 12:
            summary = "MAC绑定测试"
            test_data = "MAC地址和IP"

        # LAN-003 (id=13): preconditions 不完整 + topo 太简
        elif case_id == 13:
            preconditions = "路由器已配置"
            topo = "Router -> PC"

        # LAN-004 (id=14): test_data 为空 + 步骤缺少 action 细节
        elif case_id == 14:
            test_data = ""
            steps = steps.replace('"action":"设置LAN IP为172.16.0.1/24"', '"action":"设置IP"')

        # LAN-005 (id=15): topo 缺失 + summary 太笼统
        elif case_id == 15:
            topo = ""
            summary = "测试第二IP功能"

        # LAN-006 (id=16): preconditions 为空 + test_data 不完整
        elif case_id == 16:
            preconditions = ""
            test_data = "域名: www.qq.com"

        # LAN-007 (id=17): name 不准确 + 步骤 expected 为空
        elif case_id == 17:
            name = "ARP相关测试"
            orig_steps = json.loads(steps)
            for s in orig_steps:
                if s["step_no"] in [4, 5]:
                    s["expected"] = ""
            steps = json.dumps(orig_steps, ensure_ascii=False)

        # LAN-008 (id=18): summary 太简单 + preconditions 不完整
        elif case_id == 18:
            summary = "聚合口测试"
            preconditions = "路由器开机"

        # LAN-009 (id=19): test_data 缺失 + topo 过于简单
        elif case_id == 19:
            test_data = ""
            topo = "Router -> Switch"

        # LAN-010 (id=20): summary 质量低 + 步骤逻辑断层
        elif case_id == 20:
            summary = "STP测试"
            orig_steps = json.loads(steps)
            # 删除步骤3，造成逻辑断层
            if len(orig_steps) >= 5:
                del orig_steps[2]
                for i, s in enumerate(orig_steps):
                    s["step_no"] = i + 1
            steps = json.dumps(orig_steps, ensure_ascii=False)

        # WLS-001 (id=21): name 过长 + summary 只有半句
        elif case_id == 21:
            name = "2.4G频段无线网络开启与关闭以及SSID广播开关功能测试验证"
            summary = "测试2.4G"

        # WLS-002 (id=22): test_data 为空 + preconditions 过于简略
        elif case_id == 22:
            test_data = ""
            preconditions = "WiFi已开启"

        # WLS-003 (id=23): topo 缺失 + 步骤 action 模糊
        elif case_id == 23:
            topo = ""
            steps = steps.replace('"action":"设置加密方式为WPA2-PSK+AES"', '"action":"改加密"')

        # WLS-004 (id=24): summary 只重复 name + test_data 缺失
        elif case_id == 24:
            summary = "信道自动或手动选择测试"
            test_data = ""

        # WLS-005 (id=25): preconditions 为空 + topo 太简
        elif case_id == 25:
            preconditions = ""
            topo = "Router <--> Phone"

        # WLS-006 (id=26): name 不够准确 + summary 含义模糊
        elif case_id == 26:
            name = "WPS功能测试"
            summary = "测试快速连接"

        # WLS-007 (id=27): test_data 缺失 + 步骤 expected 模糊
        elif case_id == 27:
            test_data = ""
            orig_steps = json.loads(steps)
            for s in orig_steps:
                if s["step_no"] in [1, 4]:
                    s["expected"] = "功能正常"
            steps = json.dumps(orig_steps, ensure_ascii=False)

        # WLS-008 (id=28): topo 缺失 + summary 太简
        elif case_id == 28:
            topo = ""
            summary = "访客网络测试"

        # WLS-009 (id=29): preconditions 不完整 + test_data 不明确
        elif case_id == 29:
            preconditions = "WiFi已开启"
            test_data = "定时规则"

        # WLS-010 (id=30): name 过长 + 步骤逻辑顺序打乱
        elif case_id == 30:
            name = "5GHz频段独立SSID和信道和带宽的完整配置功能验证"
            orig_steps = json.loads(steps)
            if len(orig_steps) >= 5:
                orig_steps[1], orig_steps[3] = orig_steps[3], orig_steps[1]
            steps = json.dumps(orig_steps, ensure_ascii=False)

        updates.append((name, summary, preconditions, topo, test_data, steps, case_id))

    # 批量更新
    for name, summary, preconditions, topo, test_data, steps, case_id in updates:
        cur.execute(
            """UPDATE ai_tc_cases 
               SET name=%s, summary=%s, preconditions=%s, topo=%s,
                   test_data=%s, steps=%s, review_status=0, update_time=NOW()
               WHERE id=%s""",
            (name, summary, preconditions, topo, test_data, steps, case_id),
        )

    conn.commit()
    cur.close()
    conn.close()

    print("=" * 60)
    print("已改造 30 条用例，引入各类质量问题：")
    print()
    print("问题类型分布:")
    print("  - 用例名称过长/不准确: WAN-001, WAN-008, WAN-010, LAN-001, LAN-007, WLS-001, WLS-006, WLS-010")
    print("  - 测试思想过于简单/模糊: WAN-001, WAN-003, WAN-007, LAN-002, LAN-005, LAN-008, LAN-010, WLS-001, WLS-004, WLS-008")
    print("  - 前置条件不完整/为空: WAN-002, WAN-005, WAN-007, WAN-009, LAN-003, LAN-006, WLS-002, WLS-005, WLS-009")
    print("  - 测试数据缺失/不明确: WAN-001, WAN-003, WAN-006, LAN-002, LAN-004, LAN-006, LAN-009, WLS-002, WLS-004, WLS-007, WLS-009")
    print("  - 拓扑信息缺失/过于简单: WAN-002, WAN-006, LAN-003, LAN-005, LAN-009, WLS-003, WLS-005, WLS-008")
    print("  - 步骤问题(缺少expected/action模糊/逻辑乱序): WAN-002, WAN-004, WAN-005, WAN-008, LAN-001, LAN-004, LAN-007, LAN-010, WLS-001, WLS-003, WLS-007, WLS-010")
    print()
    print("所有用例的 review_status 已重置为 0（未审核）")
    print("=" * 60)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "degrade"
    if cmd == "restore":
        restore_cases()
    else:
        degrade_cases()
