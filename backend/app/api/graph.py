"""
图谱相关API路由
采用项目上下文机制，服务端持久化状态
"""

import json
import os
from pathlib import Path
from flask import request, jsonify

from . import graph_bp, api_error_payload
from ..config import Config
from ..services.consumer import ConsumerBriefAdapter
from ..services.consumer.document_ingest import DocumentIngestService
from ..services.consumer.models import ResearchSourceLane, ResearchSourceType
from ..services.consumer.persona_pack_registry import get_registry, PersonaPackClass, list_builtin_persona_packs
from ..services.consumer.source_registry import SourceRegistry
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..utils.locale import t
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus
from ..services.application.graph_app_service import GraphAppService

# 获取日志器
logger = get_logger('miroconsumer.api')


def _normalize_consumer_brief_payload(raw_payload):
    """Parse a consumer brief from form/json payloads into a persisted summary."""
    if raw_payload is None:
        return None

    payload = raw_payload
    if isinstance(raw_payload, str):
        raw_payload = raw_payload.strip()
        if not raw_payload:
            return None
        payload = json.loads(raw_payload)

    brief = ConsumerBriefAdapter.from_payload(payload)
    return brief.to_summary()


def _get_consumer_graph_payload(project):
    if not project or project.project_type != "consumer_test":
        return None
    return ProjectManager.load_consumer_graph_payload(project.project_id)


def _ingest_project_files_into_research_workspace(project_id: str, file_texts: list) -> None:
    """Register uploaded files as Lane A sources and ingest their text into the research workspace."""
    if not file_texts:
        return
    registry = SourceRegistry(project_id, upload_root=Config.UPLOAD_FOLDER)
    ingest = DocumentIngestService(project_id, upload_root=Config.UPLOAD_FOLDER)
    for file_info in file_texts:
        original_filename = file_info.get("original_filename", "unknown")
        text = file_info.get("text", "")
        if not text:
            continue
        source = registry.register_source(
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label=f"User upload: {original_filename}",
            uri=file_info.get("path", ""),
        )
        ingest.ingest_text(
            source_id=source.source_id,
            text=text,
            title=original_filename,
        )


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


@graph_bp.route('/persona-packs', methods=['GET'])
def list_persona_packs():
    """
    列出可用的内置 persona packs
    """
    try:
        project_id = request.args.get("project_id", "").strip()
        if project_id:
            project_persona_dir = Path(Config.UPLOAD_FOLDER) / "projects" / project_id / "persona_packs"
            packs = get_registry(project_persona_dir=project_persona_dir).list_packs()
        else:
            packs = list_builtin_persona_packs()
        return jsonify({
            "success": True,
            "data": [p.to_summary() for p in packs]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== 项目管理接口 ==============

@graph_bp.route('/project/<project_id>/persona-packs', methods=['POST'])
def upload_project_persona_pack(project_id: str):
    """Upload a custom persona pack for an existing project."""
    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    persona_pack_file = request.files.get('persona_pack_file')
    if not persona_pack_file or not persona_pack_file.filename:
        return jsonify({
            "success": False,
            "error": "persona_pack_file is required"
        }), 400
    if not persona_pack_file.filename.lower().endswith('.json'):
        return jsonify({
            "success": False,
            "error": "Persona pack file must be a JSON file (.json)"
        }), 400

    try:
        raw_json = persona_pack_file.read().decode('utf-8')
        project_persona_dir = Path(Config.UPLOAD_FOLDER) / "projects" / project.project_id / "persona_packs"
        registry = get_registry(project_persona_dir=project_persona_dir)
        pack_class_value = request.form.get("pack_class", PersonaPackClass.Custom.value)
        try:
            pack_class = PersonaPackClass(str(pack_class_value).strip().lower())
        except ValueError:
            pack_class = PersonaPackClass.Custom
        pack_origin = request.form.get("pack_origin", "uploaded_persona_pack").strip() or "uploaded_persona_pack"
        pack_meta = registry.register_custom_pack(
            raw_json=raw_json,
            label=request.form.get("label") or persona_pack_file.filename,
            description=request.form.get("description", ""),
            pack_class=pack_class,
            pack_origin=pack_origin,
        )
        return jsonify({
            "success": True,
            "data": pack_meta.to_summary(),
        })
    except (ValueError, UnicodeDecodeError) as e:
        return jsonify({
            "success": False,
            "error": f"Invalid persona pack file: {e}"
        }), 400
    except Exception as e:
        logger.error(f"Upload persona pack failed: {e}")
        return jsonify(api_error_payload(str(e))), 500


@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    获取项目详情
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
    列出所有项目
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    删除项目
    """
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": t('api.projectDeleteFailed', id=project_id)
        }), 404

    return jsonify({
        "success": True,
        "message": t('api.projectDeleted', id=project_id)
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
    重置项目状态（用于重新构建图谱）
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": t('api.projectNotFound', id=project_id)
        }), 404

    # 重置到本体已生成状态
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.delete_consumer_graph_payload(project.project_id)
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": t('api.projectReset', id=project_id),
        "data": project.to_dict()
    })


# ============== 接口1：上传文件并生成本体 ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    接口1：上传文件，分析生成本体定义
    
    请求方式：multipart/form-data
    
    参数：
        files: 上传的文件（PDF/MD/TXT），可多个
        simulation_requirement: 模拟需求描述（必填）
        project_name: 项目名称（可选）
        additional_context: 额外说明（可选）
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== 开始生成本体定义 ===")
        
        # 获取参数
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        project_type = request.form.get('project_type', 'default').strip() or 'default'
        consumer_brief = _normalize_consumer_brief_payload(request.form.get('consumer_brief'))
        
        logger.debug(f"项目名称: {project_name}")
        logger.debug(f"模拟需求: {simulation_requirement[:100]}...")
        
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationRequirement')
            }), 400
        
        # 获取上传的文件
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": t('api.requireFileUpload')
            }), 400
        
        # 创建项目
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        project.project_type = project_type
        logger.info(f"创建项目: {project.project_id}")

        # 处理可选的自定义 persona pack 上传
        persona_pack_file = request.files.get('persona_pack_file')
        if persona_pack_file and persona_pack_file.filename:
            if not persona_pack_file.filename.lower().endswith('.json'):
                ProjectManager.delete_project(project.project_id)
                return jsonify({
                    "success": False,
                    "error": "Persona pack file must be a JSON file (.json)"
                }), 400
            try:
                raw_json = persona_pack_file.read().decode('utf-8')
                project_persona_dir = Path(Config.UPLOAD_FOLDER) / "projects" / project.project_id / "persona_packs"
                registry = get_registry(project_persona_dir=project_persona_dir)
                pack_meta = registry.register_custom_pack(
                    raw_json=raw_json,
                    label=persona_pack_file.filename,
                    description=f"Custom persona pack uploaded as {persona_pack_file.filename}",
                    pack_class=PersonaPackClass.Custom,
                )
                if consumer_brief is None:
                    consumer_brief = {}
                consumer_brief["persona_pack_selection"] = {
                    "pack_id": pack_meta.pack_id,
                    "pack_class": PersonaPackClass.Custom.value,
                    "custom_upload": True,
                }
                logger.info(f"Custom persona pack registered: {pack_meta.pack_id}")
            except (ValueError, UnicodeDecodeError) as e:
                ProjectManager.delete_project(project.project_id)
                return jsonify({
                    "success": False,
                    "error": f"Invalid persona pack file: {e}"
                }), 400

        project.consumer_brief = consumer_brief
        
        # 保存文件并提取文本
        document_texts = []
        all_text = ""
        file_texts = []

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # 保存文件到项目目录
                file_info = ProjectManager.save_file_to_project(
                    project.project_id,
                    file,
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })

                # 提取文本
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
                file_texts.append({
                    "original_filename": file_info["original_filename"],
                    "path": file_info["path"],
                    "text": text,
                })

        # Wire Lane A research workspace ingestion for uploaded materials
        _ingest_project_files_into_research_workspace(project.project_id, file_texts)

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": t('api.noDocProcessed')
            }), 400
        
        # 保存提取的文本
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"文本提取完成，共 {len(all_text)} 字符")
        
        # 生成本体
        logger.info("调用 LLM 生成本体定义...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )
        
        # 保存本体到项目
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"本体生成完成: {entity_count} 个实体类型, {edge_count} 个关系类型")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== 本体生成完成 === 项目ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        return jsonify(api_error_payload(str(e))), 500


# ============== 接口2：构建图谱 ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    接口2：根据project_id构建图谱
    
    请求（JSON）：
        {
            "project_id": "proj_xxxx",  // 必填，来自接口1
            "graph_name": "图谱名称",    // 可选
            "chunk_size": 500,          // 可选，默认500
            "chunk_overlap": 50         // 可选，默认50
        }
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "图谱构建任务已启动"
            }
        }
    """
    try:
        logger.info("=== 开始构建图谱 ===")

        # 解析请求
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"请求参数: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": t('api.requireProjectId')
            }), 400
        
        # 获取项目
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=project_id)
            }), 404

        # 检查项目状态
        force = data.get('force', False)  # 强制重新构建
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": t('api.ontologyNotGenerated')
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": t('api.graphBuilding'),
                "task_id": project.graph_build_task_id
            }), 400
        
        # 如果强制重建，重置状态
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
            ProjectManager.delete_consumer_graph_payload(project.project_id)
        
        # 获取配置
        graph_name = data.get('graph_name', project.name or 'MiroConsumer Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # 更新项目配置
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # 获取提取的文本
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": t('api.textNotFound')
            }), 400
        
        # 获取本体
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": t('api.ontologyNotFound')
            }), 400

        if project.project_type == "consumer_test":
            task_manager = TaskManager()
            task_id = task_manager.create_task(f"构建消费测试图谱: {graph_name}")
            logger.info(f"创建消费测试图谱任务: task_id={task_id}, project_id={project_id}")

            project.status = ProjectStatus.GRAPH_BUILDING
            project.graph_build_task_id = task_id
            project.graph_id = None
            project.error = None
            ProjectManager.delete_consumer_graph_payload(project.project_id)
            ProjectManager.save_project(project)

            try:
                GraphAppService.build_consumer_graph_sync(project, text, task_manager, task_id)
            except Exception:
                raise

            return jsonify({
                "success": True,
                "data": {
                    "project_id": project_id,
                    "task_id": task_id,
                    "message": t('api.graphBuildStarted', taskId=task_id)
                }
            })

        # 检查配置
        errors = []
        if not Config.ZEP_API_KEY:
            errors.append(t('api.zepApiKeyMissing'))
        if errors:
            logger.error(f"配置错误: {errors}")
            return jsonify({
                "success": False,
                "error": t('api.configError', details="; ".join(errors))
            }), 500

        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"构建图谱: {graph_name}")
        logger.info(f"创建图谱构建任务: task_id={task_id}, project_id={project_id}")

        # 更新项目状态
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)

        GraphAppService.spawn_legacy_graph_build(
            project, task_id, graph_name, text, ontology,
            chunk_size, chunk_overlap
        )

        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": t('api.graphBuildStarted', taskId=task_id)
            }
        })
        
    except Exception as e:
        return jsonify(api_error_payload(str(e))), 500


# ============== 任务查询接口 ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    查询任务状态
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": t('api.taskNotFound', id=task_id)
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    列出所有任务
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== 图谱数据接口 ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    获取图谱数据（节点和边）
    """
    try:
        if graph_id.startswith("consumer_"):
            project_id = graph_id[len("consumer_"):]
            project = ProjectManager.get_project(project_id)
            graph_payload = _get_consumer_graph_payload(project)
            if graph_payload:
                return jsonify({
                    "success": True,
                    "data": graph_payload
                })
            return jsonify({
                "success": False,
                "error": f"Consumer graph not found: {graph_id}"
            }), 404

        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify(api_error_payload(str(e))), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    删除Zep图谱
    """
    try:
        if graph_id.startswith("consumer_"):
            project_id = graph_id[len("consumer_"):]
            project = ProjectManager.get_project(project_id)
            graph_payload = _get_consumer_graph_payload(project)

            if not project or graph_id != project.graph_id or not graph_payload:
                return jsonify({
                    "success": False,
                    "error": f"Consumer graph not found: {graph_id}"
                }), 404

            ProjectManager.delete_consumer_graph_payload(project_id)
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
            project.status = (
                ProjectStatus.ONTOLOGY_GENERATED if project.ontology else ProjectStatus.CREATED
            )
            ProjectManager.save_project(project)

            return jsonify({
                "success": True,
                "message": t('api.graphDeleted', id=graph_id)
            })

        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": t('api.graphDeleted', id=graph_id)
        })
        
    except Exception as e:
        return jsonify(api_error_payload(str(e))), 500
