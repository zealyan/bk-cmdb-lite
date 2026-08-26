import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
sys.path.insert(0, '.')
from app import create_app
from app.service.topo_service import get_mainline_children
app = create_app()
with app.app_context():
    print("=== biz3 业务下首位子节点（应为空闲机池）===")
    ch = get_mainline_children(3, 'biz', 3, with_statistics=True)
    for c in ch[:3]:
        print(" ", c['bk_obj_id'], c['bk_inst_id'], c['bk_inst_name'],
              'bk_obj_name=', c['bk_obj_name'], 'default=', c['default'],
              'is_idle_set=', c['is_idle_set'], 'is_leaf=', c['is_leaf'])
    print("  总数:", len(ch))
    print()
    print("=== biz2 业务下子节点（空闲机池 + 3演示集群）===")
    ch2 = get_mainline_children(2, 'biz', 2, with_statistics=True)
    for c in ch2:
        print(" ", c['bk_obj_id'], c['bk_inst_id'], c['bk_inst_name'],
              'bk_obj_name=', c['bk_obj_name'], 'default=', c['default'], 'is_idle_set=', c['is_idle_set'])
    print()
    print("=== idle pool 下层模块（空闲机/故障机，图标应为内部图标）===")
    idle = ch[0]
    mods = get_mainline_children(3, 'set', idle['bk_inst_id'], with_statistics=True)
    for m in mods:
        print(" ", m['bk_obj_id'], m['bk_inst_id'], m['bk_inst_name'],
              'bk_obj_name=', m['bk_obj_name'], 'default=', m['default'], 'is_leaf=', m['is_leaf'])
