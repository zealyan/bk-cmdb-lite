"""
CLI `scaffold from-csv` 测试（设计文档 §5.6.3）。

覆盖：
- 正常生成与 seed 同构目录（classifications/models/attributes_<oid>/instances_<oid>）
- 保留列加前缀 u_ 区分（bk_obj_id→u_bk_obj_id、id→u_id），中文名仍取原 key
- 缺 bk_inst_name 时自动补（属性必填 + 实例列占位 bk_<model>_<行号>）
- 规则 1/2/5 校验失败（文件名大写 / 表头非法 / 重复列）→ 退出码 2 且零落盘
- --dry-run 仅预演不写盘
- from-csv → scaffold apply 端到端落库（模型 + 属性 + 实例）

做法：from-csv 为纯文件操作，无需预置库；端到端用例拷贝 cmdb_dev.db 到沙箱库，
全程用 --db 指向沙箱，避免污染开发库。
"""
import os
import sys
import csv
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.cli.cmdb as cmdb

REAL_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cmdb_dev.db')
assert os.path.exists(REAL_DB), f"开发库缺失: {REAL_DB}"


def _write_input(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _read_rows(path):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def _gen_dir(out_dir):
    """返回 from-csv 生成的 12 位时间戳子目录路径（假设仅一次生成）。"""
    subs = [d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d))]
    assert len(subs) == 1, f"期望仅一个时间戳目录，实际: {subs}"
    return os.path.join(out_dir, subs[0])


def test_from_csv_generates_seed_like_dir():
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'servers.csv')
        _write_input(csv_path, ['bk_inst_name', 'ip', 'region', 'owner'],
                     [['web-01', '10.0.0.1', 'sh', 'alice'],
                      ['web-02', '10.0.0.2', 'bj', 'bob']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 0
        d = _gen_dir(out)
        files = set(os.listdir(d))
        assert files == {'classifications.csv', 'models.csv',
                         'attributes_servers.csv', 'instances_servers.csv'}, files
        # models.csv
        mrows = _read_rows(os.path.join(d, 'models.csv'))
        assert mrows[1][0] == 'servers' and mrows[1][1] == '模型-servers'
        # attributes：3 行表头（13 列）+ 4 数据行
        arows = _read_rows(os.path.join(d, 'attributes_servers.csv'))
        assert arows[2] == cmdb._FC_ATTR_EN, "英文名行须为 13 列 seed 模板"
        data = arows[3:]
        assert len(data) == 4
        assert data[0][0] == 'bk_inst_name' and data[0][2] == 'singlechar'
        assert data[0][9] == 'true', "bk_inst_name 应必填"
        assert data[1][0] == 'ip' and data[1][2] == 'singlechar' and data[1][9] == 'false'
        # instances：表头回映输入，数据原样
        irows = _read_rows(os.path.join(d, 'instances_servers.csv'))
        assert irows[0] == ['bk_inst_name', 'ip', 'region', 'owner']
        assert len(irows) == 3
        assert irows[1][0] == 'web-01'
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_missing_bk_inst_name_auto_fills():
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'missing_name.csv')
        _write_input(csv_path, ['ip', 'region'],
                     [['10.0.0.1', 'sh'], ['10.0.0.2', 'bj']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 0
        d = _gen_dir(out)
        arows = _read_rows(os.path.join(d, 'attributes_missing_name.csv'))
        data = arows[3:]
        assert len(data) == 3  # bk_inst_name + ip + region
        name_row = [r for r in data if r[0] == 'bk_inst_name'][0]
        assert name_row[2] == 'singlechar' and name_row[9] == 'true'
        irows = _read_rows(os.path.join(d, 'instances_missing_name.csv'))
        assert irows[0][0] == 'bk_inst_name'
        assert irows[1][0] == 'bk_missing_name_1'
        assert irows[2][0] == 'bk_missing_name_2'
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_reserved_columns_prefixed():
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'with_sys.csv')
        _write_input(csv_path, ['bk_inst_name', 'ip', 'bk_obj_id', 'id'],
                     [['srv-01', '10.0.0.1', 'app', '1001'],
                      ['srv-02', '10.0.0.2', 'db', '1002']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 0
        d = _gen_dir(out)
        arows = _read_rows(os.path.join(d, 'attributes_with_sys.csv'))
        data = arows[3:]
        # 中文名（col 1）仍取原 key，属性 id（col 0）被加前缀
        by_name = {r[1]: r[0] for r in data}
        assert by_name['bk_obj_id'] == 'u_bk_obj_id', by_name
        assert by_name['id'] == 'u_id', by_name
        irows = _read_rows(os.path.join(d, 'instances_with_sys.csv'))
        assert 'u_bk_obj_id' in irows[0] and 'bk_obj_id' not in irows[0]
        assert irows[1][irows[0].index('u_bk_obj_id')] == 'app'
        assert irows[1][irows[0].index('u_id')] == '1001'
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_validation_failure_uppercase_filename():
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'Servers.csv')
        _write_input(csv_path, ['bk_inst_name', 'ip'], [['a', '1.1.1.1']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 2
        assert os.listdir(out) == [], "校验失败不应生成任何目录"
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_validation_failure_bad_header():
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'badcols.csv')
        _write_input(csv_path, ['bk_inst_name', 'IP 地址', '1st_field'],
                     [['a', '1.1.1.1', 'x']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 2
        assert os.listdir(out) == []
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_validation_failure_duplicate_column():
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'dup.csv')
        _write_input(csv_path, ['bk_inst_name', 'ip', 'ip'],
                     [['a', '1.1.1.1', '2.2.2.2']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 2
        assert os.listdir(out) == []
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_dry_run_no_write(capsys):
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'servers.csv')
        _write_input(csv_path, ['bk_inst_name', 'ip'], [['a', '1.1.1.1']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path,
                        '--out-dir', out, '--dry-run', '--json'])
        assert rc == 0
        assert os.listdir(out) == [], "dry-run 不应写盘"
        out_json = capsys.readouterr().out
        assert '"model_id": "servers"' in out_json, out_json
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)


def test_from_csv_then_apply_end_to_end():
    db = tempfile.mktemp(suffix='.db', prefix='fc_apply_')
    shutil.copy(REAL_DB, db)
    out = tempfile.mkdtemp(prefix='fc_out_')
    src = tempfile.mkdtemp(prefix='fc_src_')
    try:
        csv_path = os.path.join(src, 'servers.csv')
        _write_input(csv_path, ['bk_inst_name', 'ip', 'region', 'owner'],
                     [['web-01', '10.0.0.1', 'sh', 'alice'],
                      ['web-02', '10.0.0.2', 'bj', 'bob']])
        rc = cmdb.main(['scaffold', 'from-csv', '--csv', csv_path, '--out-dir', out])
        assert rc == 0
        d = _gen_dir(out)
        rc = cmdb.main(['scaffold', 'apply', '--dir', d, '--db', db, '--atomic'])
        assert rc == 0
        # 校验落库
        from app.cli import db as dbmod
        dbmod.init_cli_db(db, 'development')
        with dbmod.cli_conn() as c:
            m = c.query_one("SELECT bk_obj_name FROM cc_ObjDes WHERE bk_obj_id='servers'")
            assert m and m['bk_obj_name'] == '模型-servers'
            n = c.query_one("SELECT COUNT(*) n FROM cc_ObjectBase_0_pub_servers")
            assert n['n'] == 2, n
    finally:
        os.remove(db)
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)
