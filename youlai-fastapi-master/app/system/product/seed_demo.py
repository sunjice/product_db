"""重建规格分组 + Demo 产品数据（按真实网卡/路由器规格）。"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.database import AsyncSessionLocal
from app.system.product.models import Product, ProductCategory, ProductBrand, ProductSpecGroup, ProductSpecification
from sqlalchemy import text, select


async def rebuild():
    async with AsyncSessionLocal() as db:
        # 1. 软删除旧的 Demo 产品及其规格
        await db.execute(text("UPDATE products SET is_deleted = 1 WHERE name LIKE 'Demo%'"))
        await db.execute(text("UPDATE product_specifications SET is_deleted = 1 WHERE product_id IN (SELECT id FROM products WHERE name LIKE 'Demo%')"))
        print("已清除旧 Demo 产品")

        # 2. 重建规格分组（软删除旧的，插入新的）
        await db.execute(text("UPDATE product_spec_groups SET is_deleted = 1"))
        print("已清除旧规格分组")

        # 获取分类
        cats = await db.execute(select(ProductCategory.id, ProductCategory.slug).where(ProductCategory.is_deleted == 0))
        cat_map = {row.slug: row.id for row in cats}
        nic_cat = cat_map.get("network-card")
        router_cat = cat_map.get("router")

        # ── 网卡规格分组 ──
        nic_groups = [
            ProductSpecGroup(category_id=nic_cat, name="基础参数", sort_order=1),
            ProductSpecGroup(category_id=nic_cat, name="网络协议", sort_order=2),
            ProductSpecGroup(category_id=nic_cat, name="电气与环境", sort_order=3),
            ProductSpecGroup(category_id=nic_cat, name="兼容性", sort_order=4),
        ]
        # ── 路由器规格分组 ──
        router_groups = [
            ProductSpecGroup(category_id=router_cat, name="基础参数", sort_order=1),
            ProductSpecGroup(category_id=router_cat, name="端口规格", sort_order=2),
            ProductSpecGroup(category_id=router_cat, name="无线规格", sort_order=3),
            ProductSpecGroup(category_id=router_cat, name="性能指标", sort_order=4),
            ProductSpecGroup(category_id=router_cat, name="功能特性", sort_order=5),
        ]
        db.add_all(nic_groups + router_groups)
        await db.flush()
        print(f"已插入 {len(nic_groups)} 网卡分组 + {len(router_groups)} 路由器分组")

        # 重新查询分组 ID
        all_groups = await db.execute(select(ProductSpecGroup.id, ProductSpecGroup.name, ProductSpecGroup.category_id).where(ProductSpecGroup.is_deleted == 0))
        nic_group_map = {}
        router_group_map = {}
        for g in all_groups:
            if g[2] == nic_cat:
                nic_group_map[g[1]] = g[0]
            elif g[2] == router_cat:
                router_group_map[g[1]] = g[0]

        # 获取品牌
        brands = await db.execute(select(ProductBrand.id, ProductBrand.name).where(ProductBrand.is_deleted == 0))
        brand_map = {row.name: row.id for row in brands}

        # ═══════════════ 网卡 Demo 1: Intel X710-T4L ═══════════════
        p1 = Product(
            category_id=nic_cat, brand_id=brand_map.get("Intel"),
            name="Demo Intel X710-T4L 网卡", model="X710-T4L",
            description="Intel X710 四端口万兆以太网网卡，支持 iWARP/RDMA",
            image_urls=[], status=1, sort_order=1,
        )
        db.add(p1)
        await db.flush()
        p1_specs = [
            # 基础参数
            ("基础参数", "产品型号", "X710-T4L", ""),
            ("基础参数", "接口类型", "RJ45", ""),
            ("基础参数", "端口数量", "4", "个"),
            ("基础参数", "传输速率", "10Gbps", ""),
            ("基础参数", "总线接口", "PCIe 3.0 x8", ""),
            # 网络协议
            ("网络协议", "支持协议", "TCP/IP, iSCSI, FCoE, iWARP", ""),
            ("网络协议", "RDMA", "iWARP", ""),
            ("网络协议", "SR-IOV", "支持（最大64个虚拟功能）", ""),
            ("网络协议", "校验和卸载", "TCP/UDP/SCTP", ""),
            # 电气与环境
            ("电气与环境", "功耗", "12.5", "W"),
            ("电气与环境", "工作温度", "0~55", "℃"),
            ("电气与环境", "存储温度", "-40~70", "℃"),
            ("电气与环境", "MTBF", "3,000,000", "小时"),
            # 兼容性
            ("兼容性", "操作系统", "Windows Server, Linux, VMware ESXi, FreeBSD", ""),
            ("兼容性", "认证", "FCC, CE, UL, RoHS", ""),
        ]
        for group_name, spec_name, spec_value, spec_unit in p1_specs:
            db.add(ProductSpecification(
                product_id=p1.id, group_id=nic_group_map[group_name],
                spec_name=spec_name, spec_value=spec_value, spec_unit=spec_unit,
                sort_order=p1_specs.index((group_name, spec_name, spec_value, spec_unit)),
            ))

        # ═══════════════ 网卡 Demo 2: Mellanox CX-4 Lx ═══════════════
        p2 = Product(
            category_id=nic_cat, brand_id=brand_map.get("Mellanox"),
            name="Demo Mellanox CX-4 Lx 网卡", model="CX416A-CCA",
            description="Mellanox ConnectX-4 Lx 双端口万兆网卡，支持 RoCE v2",
            image_urls=[], status=1, sort_order=2,
        )
        db.add(p2)
        await db.flush()
        p2_specs = [
            ("基础参数", "产品型号", "CX416A-CCA", ""),
            ("基础参数", "接口类型", "SFP+", ""),
            ("基础参数", "端口数量", "2", "个"),
            ("基础参数", "传输速率", "10Gbps", ""),
            ("基础参数", "总线接口", "PCIe 3.0 x8", ""),
            ("网络协议", "支持协议", "TCP/IP, iSCSI, RoCE v2, NVMe-oF", ""),
            ("网络协议", "RDMA", "RoCE v2", ""),
            ("网络协议", "SR-IOV", "支持（最大128个虚拟功能）", ""),
            ("网络协议", "校验和卸载", "TCP/UDP/IP", ""),
            ("电气与环境", "功耗", "9.5", "W"),
            ("电气与环境", "工作温度", "0~70", "℃"),
            ("电气与环境", "存储温度", "-40~85", "℃"),
            ("电气与环境", "MTBF", "4,000,000", "小时"),
            ("兼容性", "操作系统", "Windows, Linux, VMware ESXi", ""),
            ("兼容性", "认证", "FCC, CE, UL, RoHS", ""),
        ]
        for group_name, spec_name, spec_value, spec_unit in p2_specs:
            db.add(ProductSpecification(
                product_id=p2.id, group_id=nic_group_map[group_name],
                spec_name=spec_name, spec_value=spec_value, spec_unit=spec_unit,
                sort_order=p2_specs.index((group_name, spec_name, spec_value, spec_unit)),
            ))

        # ═══════════════ 路由器 Demo 1: TP-Link TL-R473GP ═══════════════
        p3 = Product(
            category_id=router_cat, brand_id=brand_map.get("TP-Link"),
            name="Demo TP-Link TL-R473GP 路由器", model="TL-R473GP",
            description="TP-Link 企业级 VPN 路由器，5口千兆，支持 IPsec/PPTP/L2TP",
            image_urls=[], status=1, sort_order=1,
        )
        db.add(p3)
        await db.flush()
        p3_specs = [
            ("基础参数", "产品型号", "TL-R473GP", ""),
            ("基础参数", "CPU", "MT7621A @880MHz", ""),
            ("基础参数", "内存", "256", "MB"),
            ("基础参数", "闪存", "32", "MB"),
            ("端口规格", "WAN口", "1", "个"),
            ("端口规格", "LAN口", "4", "个"),
            ("端口规格", "端口速率", "10/100/1000Mbps", ""),
            ("端口规格", "PoE输出", "支持（4口IEEE 802.3af）", ""),
            ("无线规格", "WiFi标准", "不支持（有线路由器）", ""),
            ("无线规格", "频段", "无", ""),
            ("无线规格", "天线", "无", ""),
            ("性能指标", "吞吐量", "900", "Mbps"),
            ("性能指标", "并发连接数", "20000", ""),
            ("性能指标", "VPN隧道数", "100", "条"),
            ("功能特性", "VPN类型", "IPsec, PPTP, L2TP", ""),
            ("功能特性", "QoS", "支持（基于IP/端口/协议）", ""),
            ("功能特性", "防火墙", "支持（SPI, MAC过滤, URL过滤）", ""),
            ("功能特性", "管理方式", "Web, SNMP, TR069", ""),
        ]
        for group_name, spec_name, spec_value, spec_unit in p3_specs:
            db.add(ProductSpecification(
                product_id=p3.id, group_id=router_group_map[group_name],
                spec_name=spec_name, spec_value=spec_value, spec_unit=spec_unit,
                sort_order=p3_specs.index((group_name, spec_name, spec_value, spec_unit)),
            ))

        # ═══════════════ 路由器 Demo 2: ASUS RT-AX86U ═══════════════
        p4 = Product(
            category_id=router_cat, brand_id=brand_map.get("ASUS"),
            name="Demo ASUS RT-AX86U 路由器", model="RT-AX86U",
            description="ASUS WiFi 6 电竞路由器，双频5700Mbps，2.5G口",
            image_urls=[], status=1, sort_order=2,
        )
        db.add(p4)
        await db.flush()
        p4_specs = [
            ("基础参数", "产品型号", "RT-AX86U", ""),
            ("基础参数", "CPU", "BCM4906 @1.8GHz 双核", ""),
            ("基础参数", "内存", "1024", "MB"),
            ("基础参数", "闪存", "256", "MB"),
            ("端口规格", "WAN口", "1", "个"),
            ("端口规格", "LAN口", "4", "个"),
            ("端口规格", "端口速率", "10/100/1000/2500Mbps", ""),
            ("端口规格", "USB口", "2×USB 3.0", ""),
            ("无线规格", "WiFi标准", "WiFi 6 (802.11ax)", ""),
            ("无线规格", "频段", "2.4GHz + 5GHz 双频", ""),
            ("无线规格", "速率", "5700", "Mbps"),
            ("无线规格", "天线", "3根外置高增益", ""),
            ("无线规格", "MIMO", "2x2 MU-MIMO (2.4G) + 4x4 MU-MIMO (5G)", ""),
            ("性能指标", "吞吐量", "5700", "Mbps"),
            ("性能指标", "并发连接数", "50000", ""),
            ("性能指标", "VPN吞吐量", "350", "Mbps"),
            ("功能特性", "VPN类型", "PPTP, L2TP, OpenVPN, WireGuard", ""),
            ("功能特性", "QoS", "支持（Adaptive QoS）", ""),
            ("功能特性", "防火墙", "支持（SPI, DoS防护）", ""),
            ("功能特性", "管理方式", "Web, ASUS Router App", ""),
        ]
        for group_name, spec_name, spec_value, spec_unit in p4_specs:
            db.add(ProductSpecification(
                product_id=p4.id, group_id=router_group_map[group_name],
                spec_name=spec_name, spec_value=spec_value, spec_unit=spec_unit,
                sort_order=p4_specs.index((group_name, spec_name, spec_value, spec_unit)),
            ))

        await db.commit()
        print(f"\n已插入 4 个 Demo 产品：")
        print(f"  网卡: Intel X710-T4L ({len(p1_specs)}条规格), Mellanox CX-4 Lx ({len(p2_specs)}条规格)")
        print(f"  路由器: TP-Link TL-R473GP ({len(p3_specs)}条规格), ASUS RT-AX86U ({len(p4_specs)}条规格)")


if __name__ == "__main__":
    asyncio.run(rebuild())
