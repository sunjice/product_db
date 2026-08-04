"""normalize_test_data_fields

规范化测试数据字段：project_prefix 改为短缩写、external_id 改为数字编号、name 改为英文标识。

Revision ID: 4e01c2c52b72
Revises: e2f3a4b5c6d7
Create Date: 2026-08-04 23:38:44.828238
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4e01c2c52b72'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── project prefix 映射 ──────────────────────────────────────────
_PROJECT_PREFIX_MAP = {
    'router': 'RT',
    'NIC': 'NC',
    'switch': 'SW',
    'testx': 'TX',
}

_PROJECT_PREFIX_REVERSE = {v: k for k, v in _PROJECT_PREFIX_MAP.items()}

# ── case name 映射 (id → new English name) ──────────────────────
_CASE_NAME_MAP = {
    1:  'pppoe_dial_connect_stability',
    2:  'dhcp_wan_ip_acquire',
    3:  'static_ip_config',
    4:  'wan_mac_clone',
    5:  'mtu_config',
    6:  'manual_dns_config',
    7:  'wan_speed_duplex',
    8:  'multi_wan_test',
    9:  'wan_auto_reconnect',
    10: 'nat_port_mapping',
    11: 'lan_dhcp_server',
    12: 'dhcp_mac_binding',
    13: 'lan_ip_subnet_change',
    14: 'subnet_mask_config',
    15: 'secondary_ip_binding',
    16: 'dns_proxy_forward',
    17: 'arp_test',
    18: 'lacp_config',
    19: 'vlan_sub_interface',
    20: 'stp_config',
    21: 'wireless_2g_enable_disable',
    22: 'ssid_broadcast_hidden',
    23: 'wifi_encryption_wpa2_wpa3',
    24: 'wifi_channel_select',
    25: 'wifi_tx_power_adjust',
    26: 'wps_test',
    27: 'wifi_mac_filter',
    28: 'guest_network_isolation',
    29: 'wifi_schedule_onoff',
    30: 'wireless_5g_config',
    31: 'user_login_test',
    32: 'login_invalid_password',
    33: 'login_empty_password',
    34: 'login_remember_password',
    35: 'login_logout',
}


def upgrade() -> None:
    # 1. 更新项目 prefix 为短缩写
    for old_pfx, new_pfx in _PROJECT_PREFIX_MAP.items():
        op.execute(
            f"UPDATE ai_tc_projects SET prefix = '{new_pfx}' WHERE prefix = '{old_pfx}'"
        )

    # 2. 用例 external_id 改为项目内自增数字编号（001、002…）
    op.execute("""
        UPDATE ai_tc_cases c
        SET external_id = LPAD(seq.rn::text, 3, '0')
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS rn
            FROM ai_tc_cases
            WHERE is_deleted = 0
        ) seq
        WHERE c.id = seq.id
    """)

    # 3. 用例 name 改为英文标识
    for case_id, new_name in _CASE_NAME_MAP.items():
        op.execute(f"UPDATE ai_tc_cases SET name = '{new_name}' WHERE id = {case_id}")


def downgrade() -> None:
    # 1. 恢复项目 prefix
    for new_pfx, old_pfx in _PROJECT_PREFIX_REVERSE.items():
        op.execute(
            f"UPDATE ai_tc_projects SET prefix = '{old_pfx}' WHERE prefix = '{new_pfx}'"
        )

    # 2. 恢复用例 external_id
    op.execute("""
        UPDATE ai_tc_cases c
        SET external_id = (
            CASE
                WHEN c.suite_id IN (1)  THEN 'WAN-'  || LPAD(c.id::text, 3, '0')
                WHEN c.suite_id IN (2)  THEN 'LAN-'  || LPAD((c.id - 10)::text, 3, '0')
                WHEN c.suite_id IN (3)  THEN 'WLS-'  || LPAD((c.id - 20)::text, 3, '0')
                WHEN c.suite_id IN (11) THEN 'TC'    || LPAD((c.id - 30)::text, 3, '0')
                ELSE 'UNK-' || LPAD(c.id::text, 3, '0')
            END
        )
        WHERE is_deleted = 0
    """)

    # 3. 恢复用例 name（无法精确回退，标记占位）
    name_list = "', '".join(_CASE_NAME_MAP.values())
    op.execute(
        f"UPDATE ai_tc_cases SET name = '__downgraded__' || id::text WHERE name IN ('{name_list}')"
    )
