"""Stdlib workspace orchestration over existing preparation and adapter contracts."""
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import shlex
import shutil
import sys

from cli_adapters.common import AdapterError, canonical, checked_path, read_regular, sha256, strict_json
from cli_adapters.collection import snapshot
from cli_adapters.plans import plan
from scripts import engineering

ROOT = engineering.ROOT
EVIDENCE = ('trace.jsonl', 'normalized-trace.json', 'collection.json', 'evaluation.json')


def location(value):
    raw = os.fspath(value)
    if not raw or '\\' in raw or '..' in Path(raw).parts or any(ord(c) < 32 for c in raw):
        raise AdapterError('路径不得包含 ..、反斜杠或控制字符')
    return checked_path(raw)


def task_identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[BSGDK]0[1-5](?:-slice)?|S04-spring)', value):
        raise AdapterError('请提供明确 task/implementation ID，例如 B01、B01-slice、S04-spring')
    task = value.removesuffix('-slice')
    directory = engineering.task_path(task)
    return task, task if task in engineering.VARIANTS else task + '-slice', directory


def doctor(provider=None):
    names = ['python3', 'java', 'javac', 'git'] + ([provider] if provider else ['codex', 'claude'])
    checks = [{'name': name, 'available_on_path': bool(shutil.which(name))} for name in names]
    return {'schema_version': 1, 'command': 'doctor', 'checks': checks,
            'python_version': '.'.join(map(str, sys.version_info[:3])),
            'offline_workspace_supported': sys.version_info >= (3, 10) and os.name == 'posix',
            'agent_execution': 'not_attempted', 'credentials': 'not_read',
            'versions': 'CLI/Java versions not probed; manually verify Java 21 and CLI flags',
            'missing_tools': [c['name'] for c in checks if not c['available_on_path']],
            'warning': 'PATH presence does not prove version, authentication, billing, sandbox or readiness. No executable launched; no config inspected.'}


def write_json(path, value):
    path.write_bytes(canonical(value) + b'\n')


def commands(workspace, task, provider, model, cli_version):
    python = 'python3'
    base = [python, '-m', 'cli_adapters']
    preflight = ([{'step': 'prepare_workspace_git', 'cwd': str(ROOT), 'argv': ['git', '-C', str(workspace), 'init'], 'manual_only': True, 'warning': 'Run only if you decide to execute Codex later; creates outer workspace .git outside submission snapshots; baseline is not a security boundary; never touches benchmark repository'}] if provider == 'codex' else [])
    return preflight + [
        {'step': 'normalize', 'cwd': str(ROOT), 'argv': base + ['normalize', '--provider', provider, '--model', model, '--cli-version', cli_version, '--trace', str(workspace/'trace.jsonl')], 'stdout_file': str(workspace/'normalized-trace.json')},
        {'step': 'collect', 'cwd': str(ROOT), 'argv': base + ['collect', '--before', str(workspace/'baseline'), '--after', str(workspace/'candidate')], 'stdout_file': str(workspace/'collection.json')},
        {'step': 'evaluate', 'cwd': str(ROOT), 'argv': [python, 'scripts/engineering.py', 'evaluate', task, str(workspace/'candidate'), '--trusted-code', '--output', str(workspace/'evaluation.json')], 'requires_trusted_candidate': True},
        {'step': 'status', 'cwd': str(ROOT), 'argv': [python, '-m', 'experiment_tools', 'status', '--workspace', str(workspace)]}]


def initialize(task, provider, model, cli_version, workspace, auth_mode='unknown', sandbox='read-only'):
    task, implementation, source = task_identity(task)
    target = location(workspace)
    if target.exists():
        raise AdapterError('工作区必须不存在；不会覆盖已有目录或文件')
    if target == ROOT or ROOT in target.parents:
        raise AdapterError('工作区必须位于 benchmark 仓库外，避免混入 verifier/reference')
    if not target.parent.is_dir():
        raise AdapterError('请先创建工作区的父目录')
    # Validate metadata/options without creating anything or probing a CLI.
    plan(provider, ROOT, model, cli_version, 'validation only', auth_mode=auth_mode, sandbox=sandbox)
    source_hash = sha256(read_regular(source/'task.json'))
    target.mkdir(mode=0o700)
    try:
        engineering.prepare(task, target/'baseline')
        shutil.copytree(target/'baseline', target/'candidate')
        prompt = ('请完成此独立 candidate 目录中的任务。先阅读 candidate 中的 PROMPT.md，并按其指引检查实际提供的任务材料；只修改 candidate。'
                  '不要读取原仓库 reference/verifier，不要修改 baseline 或实验记录。公共开发集不是隐藏评测。\n')
        (target/'PROMPT.md').write_text(prompt, encoding='utf-8')
        command_plan = plan(provider, target/'candidate', model, cli_version, prompt, auth_mode=auth_mode, sandbox=sandbox)
        write_json(target/'command-plan.json', command_plan)
        followup = commands(target, task, provider, model, cli_version)
        write_json(target/'next-steps.json', followup)
        baseline, _ = snapshot(target/'baseline')
        manifest = {'schema_version': 1, 'run_kind': 'offline_experiment_workspace',
                    'created_at': datetime.now(timezone.utc).isoformat(), 'workspace': str(target),
                    'task_id': task, 'implementation_id': implementation, 'manifest_sha256': source_hash,
                    'provider': provider, 'model': model, 'cli_version': cli_version,
                    'metadata_provenance': 'caller_declared_not_probed', 'auth_mode': auth_mode,
                    'baseline_source_sha256': baseline['source_sha256'],
                    'artifacts_sha256': {name: sha256(read_regular(target/name)) for name in ('PROMPT.md', 'command-plan.json', 'next-steps.json')},
                    'execution_status': 'not_run', 'business_status': 'not_evaluated', 'cost_usd': None,
                    'cost_unknown_reason': 'No model execution or billing measurement',
                    'data_class': 'public_development_workspace_not_agent_result',
                    'security': 'TRUSTED LOCAL FILES ONLY; NOT A SANDBOX OR HIDDEN EVALUATION'}
        write_json(target/'manifest.json', manifest)
        guide = ['# 实验下一步（初始化不运行模型）', '',
                 'baseline/ 是原始提交快照；candidate/ 是独立副本，只编辑后者。外层 Git 仓库不保证 baseline 安全隔离。',
                 '模型和 CLI 版本由你声明，未验证。计划不执行、不联网、不读认证信息。',
                 '先检查 command-plan.json：核实本机版本支持每个参数、登录/计费路由、工具配置。',
                 'Codex 需要 Git 仓库：若之后确实决定运行，可按下方命令在外层工作区 git init；candidate 通过父目录识别仓库，不把 .git 混入提交快照。',
                 '默认 Codex read-only 不能写修复；需要写入时初始化选择 --sandbox workspace-write。',
                 'Claude 的 read-only 参数仅是接口默认值，不代表 Claude 有只读沙箱。',
                 '没有自动启动命令；未来手动运行时按计划 argv/cwd/stdin 使用外层 PROMPT.md，保留原始 trace.jsonl。',
                 '不要把 synthetic fixture 冒充真实 trace。评估将执行候选代码，仅在信任它时使用。',
                 '以下命令均在 benchmark 仓库根执行；仅是计划，没有执行。证据文件存在不等于有效或通过。', '']
        for item in followup:
            line = shlex.join(item['argv'])
            if 'stdout_file' in item:
                line += ' > ' + shlex.quote(item['stdout_file'])
            guide += ['## ' + item['step'], '```sh', line, '```', '']
        guide += ['A/B 分析需另行预注册 analysis_tools 的 plan 和真实 trial 元数据；本 manifest 不是 paired_analysis 的 plan。',
                  'baseline 是起始代码快照，不是另一个模型的对照臂。业务结果与费用始终需要独立证据。']
        (target/'GUIDE.md').write_text('\n'.join(guide)+'\n', encoding='utf-8')
    except BaseException:
        shutil.rmtree(target)
        raise
    return {'schema_version': 1, 'command': 'init', 'workspace': str(target), 'implementation_id': implementation,
            'execution_status': 'not_run', 'business_status': 'not_evaluated',
            'artifacts': ['baseline/', 'candidate/', 'PROMPT.md', 'command-plan.json', 'next-steps.json', 'manifest.json', 'GUIDE.md'],
            'next_steps': followup}


def status(workspace):
    target = location(workspace)
    manifest = strict_json(read_regular(target/'manifest.json'))
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1 or manifest.get('run_kind') != 'offline_experiment_workspace':
        raise AdapterError('不是支持的 experiment workspace manifest')
    if manifest.get('workspace') != str(target):
        raise AdapterError('工作区路径已变化；计划中的绝对路径无效，请新建工作区')
    task, implementation, source = task_identity(manifest.get('task_id'))
    if manifest.get('implementation_id') != implementation:
        raise AdapterError('manifest task/implementation ID 不一致')
    for field in ('manifest_sha256', 'baseline_source_sha256'):
        if not isinstance(manifest.get(field), str) or not re.fullmatch(r'[a-f0-9]{64}', manifest[field]):
            raise AdapterError('manifest SHA256 格式无效: ' + field)
    if sha256(read_regular(source/'task.json')) != manifest['manifest_sha256']:
        raise AdapterError('task manifest 与当前仓库不一致；无法核对任务来源')
    integrity = []
    try:
        prepared = strict_json(read_regular(target/'baseline/PREPARED.json'))
    except FileNotFoundError:
        integrity.append({'path': 'baseline/PREPARED.json', 'status': 'missing_identity_evidence'})
    else:
        if not isinstance(prepared, dict) or prepared.get('implementation_id') != implementation or prepared.get('design_id') != task.split('-')[0]:
            raise AdapterError('baseline PREPARED 与 manifest 任务身份不一致')
    artifacts = manifest.get('artifacts_sha256')
    if not isinstance(artifacts, dict) or set(artifacts) != {'PROMPT.md', 'command-plan.json', 'next-steps.json'}:
        raise AdapterError('manifest artifacts 无效')
    for name, digest in artifacts.items():
        if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise AdapterError('artifact SHA256 格式无效')
        try:
            current = sha256(read_regular(target/name))
            state = 'unchanged' if current == digest else 'changed'
        except FileNotFoundError:
            state = 'missing'
        integrity.append({'path': name, 'status': state})
    for name in ('baseline', 'candidate'):
        try:
            current, _ = snapshot(target/name)
            state = 'unchanged' if current['source_sha256'] == manifest.get('baseline_source_sha256') else 'changed'
        except FileNotFoundError:
            state = 'missing'
        integrity.append({'path': name+'/', 'status': state})
    evidence = []
    for name in EVIDENCE:
        path = location(target/name)
        if path.exists():
            # Bounded regular-file check only. Never trusts supplied success flags.
            data = read_regular(path, 16*1024*1024)
            state = 'present_unverified' if data.strip() else 'empty'
        else:
            state = 'missing'
        evidence.append({'path': name, 'status': state})
    missing = [e['path'] for e in evidence if e['status'] != 'present_unverified']
    return {'schema_version': 1, 'command': 'status', 'workspace': str(target),
            'implementation_id': manifest.get('implementation_id'), 'integrity': integrity, 'evidence': evidence,
            'missing_evidence': missing, 'execution_status': 'not_verified', 'business_status': 'not_evaluated',
            'cost_usd': None, 'next_step': 'Review GUIDE.md and command-plan.json; supply/review missing evidence' if missing else 'Review evidence authenticity, task identity and evaluator results manually',
            'warning': 'Presence/hashes are not evidence authentication; no model outcome, cost or business pass is inferred. Manifest is local and unsigned.'}
