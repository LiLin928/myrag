"""内置工作流模板"""

BUILTIN_TEMPLATES = [
    {
        "name": "RAG问答工作流",
        "category": "RAG",
        "description": "基于知识库的问答流程：检索相关文档，生成回答",
        "definition": {
            "nodes": [
                {"id": "start-1", "type": "start", "position": {"x": 250, "y": 50}, "data": {"config": {"input_variables": [{"name": "query", "type": "string", "required": True}]}}},
                {"id": "rag-1", "type": "rag", "position": {"x": 250, "y": 150}, "data": {"config": {"query_variable": "${query}", "top_k": 5}}},
                {"id": "llm-1", "type": "llm", "position": {"x": 250, "y": 250}, "data": {"config": {"model": "claude-sonnet-4-6", "prompt_template": "根据以下内容回答问题：\n\n${rag-1.concatenated_text}\n\n问题：${query}", "temperature": 0.7}}},
                {"id": "end-1", "type": "end", "position": {"x": 250, "y": 350}, "data": {"config": {"output_variables": [{"name": "response", "variable": "${llm-1.content}"}]}}},
            ],
            "edges": [
                {"id": "e-start-rag", "source": "start-1", "target": "rag-1"},
                {"id": "e-rag-llm", "source": "rag-1", "target": "llm-1"},
                {"id": "e-llm-end", "source": "llm-1", "target": "end-1"},
            ],
        },
        "tags": ["推荐", "基础"],
    },
    {
        "name": "人工审批工作流",
        "category": "approval",
        "description": "LLM生成内容后人工审核，支持批准/拒绝/修改",
        "definition": {
            "nodes": [
                {"id": "start-1", "type": "start", "position": {"x": 250, "y": 50}, "data": {"config": {"input_variables": [{"name": "content_request", "type": "string", "required": True}]}}},
                {"id": "llm-1", "type": "llm", "position": {"x": 250, "y": 150}, "data": {"config": {"model": "claude-sonnet-4-6", "prompt_template": "${content_request}", "temperature": 0.7}}},
                {"id": "human-1", "type": "human", "position": {"x": 250, "y": 250}, "data": {"config": {"title": "内容审批", "action_options": [{"label": "批准", "value": "approve"}, {"label": "拒绝", "value": "reject"}]}}},
                {"id": "condition-1", "type": "condition", "position": {"x": 250, "y": 350}, "data": {"config": {"conditions": [{"expression": "${human-1.selected_action} == 'approve'", "target_node": "end-approved"}, {"expression": "default", "target_node": "end-rejected"}]}}},
                {"id": "end-approved", "type": "end", "position": {"x": 150, "y": 450}, "data": {"config": {"output_variables": [{"name": "status", "variable": "'approved'"}, {"name": "content", "variable": "${llm-1.content}"}]}}},
                {"id": "end-rejected", "type": "end", "position": {"x": 350, "y": 450}, "data": {"config": {"output_variables": [{"name": "status", "variable": "'rejected'"}]}}},
            ],
            "edges": [
                {"id": "e-start-llm", "source": "start-1", "target": "llm-1"},
                {"id": "e-llm-human", "source": "llm-1", "target": "human-1"},
                {"id": "e-human-cond", "source": "human-1", "target": "condition-1"},
                {"id": "e-cond-approved", "source": "condition-1", "target": "end-approved"},
                {"id": "e-cond-rejected", "source": "condition-1", "target": "end-rejected"},
            ],
        },
        "tags": ["审批", "人工"],
    },
    {
        "name": "数据处理流水线",
        "category": "data",
        "description": "HTTP获取数据 -> Python处理 -> 条件分支输出",
        "definition": {
            "nodes": [
                {"id": "start-1", "type": "start", "position": {"x": 250, "y": 50}, "data": {"config": {"input_variables": [{"name": "api_url", "type": "string", "required": True}]}}},
                {"id": "http-1", "type": "http", "position": {"x": 250, "y": 150}, "data": {"config": {"url": "${api_url}", "method": "GET"}}},
                {"id": "code-1", "type": "code", "position": {"x": 250, "y": 250}, "data": {"config": {"language": "python", "code": "import json\nresult = json.loads('${http-1.body}')\nprocessed = {'data': result, 'count': len(result) if isinstance(result, list) else 1}", "output_variables": [{"name": "result", "path": "result"}]}}},
                {"id": "end-1", "type": "end", "position": {"x": 250, "y": 350}, "data": {"config": {"output_variables": [{"name": "processed_data", "variable": "${code-1.result}"}]}}},
            ],
            "edges": [
                {"id": "e-start-http", "source": "start-1", "target": "http-1"},
                {"id": "e-http-code", "source": "http-1", "target": "code-1"},
                {"id": "e-code-end", "source": "code-1", "target": "end-1"},
            ],
        },
        "tags": ["数据", "HTTP"],
    },
]