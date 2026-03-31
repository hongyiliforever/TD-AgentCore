-- TD-AgentCore 数据库初始化脚本
-- 企业级状态持久化与向量存储

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64),
    parent_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    
    task_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    
    input_data JSONB DEFAULT '{}',
    output_data JSONB,
    error_message TEXT,
    
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(128),
    total_steps INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tasks_trace_id ON tasks(trace_id);
CREATE INDEX idx_tasks_session_id ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

-- Agent 状态表
CREATE TABLE IF NOT EXISTS agent_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    agent_name VARCHAR(64) NOT NULL,
    
    status VARCHAR(32) NOT NULL DEFAULT 'idle',
    current_action VARCHAR(128),
    
    context_data JSONB DEFAULT '{}',
    execution_log JSONB DEFAULT '[]',
    
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_states_task_id ON agent_states(task_id);
CREATE INDEX idx_agent_states_agent_name ON agent_states(agent_name);
CREATE INDEX idx_agent_states_status ON agent_states(status);

-- MCP 调用日志表
CREATE TABLE IF NOT EXISTS mcp_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id VARCHAR(64) NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    
    source_agent VARCHAR(64) NOT NULL,
    target_agent VARCHAR(64) NOT NULL,
    tool_name VARCHAR(64) NOT NULL,
    
    request_data JSONB DEFAULT '{}',
    response_data JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    
    duration_ms INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_mcp_logs_trace_id ON mcp_call_logs(trace_id);
CREATE INDEX idx_mcp_logs_task_id ON mcp_call_logs(task_id);
CREATE INDEX idx_mcp_logs_source_agent ON mcp_call_logs(source_agent);
CREATE INDEX idx_mcp_logs_target_agent ON mcp_call_logs(target_agent);
CREATE INDEX idx_mcp_logs_created_at ON mcp_call_logs(created_at);

-- 行为树执行日志表
CREATE TABLE IF NOT EXISTS btree_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    agent_state_id UUID REFERENCES agent_states(id) ON DELETE CASCADE,
    
    node_name VARCHAR(128) NOT NULL,
    node_type VARCHAR(32) NOT NULL,
    node_path VARCHAR(256),
    
    status VARCHAR(32) NOT NULL,
    output_data JSONB,
    error_message TEXT,
    
    duration_ms INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_btree_logs_task_id ON btree_execution_logs(task_id);
CREATE INDEX idx_btree_logs_agent_state_id ON btree_execution_logs(agent_state_id);
CREATE INDEX idx_btree_logs_status ON btree_execution_logs(status);

-- Agent 长期记忆表（向量存储）
CREATE TABLE IF NOT EXISTS agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) NOT NULL,
    agent_name VARCHAR(64) NOT NULL,
    
    memory_type VARCHAR(32) NOT NULL DEFAULT 'conversation',
    content TEXT NOT NULL,
    content_embedding vector(1536),
    
    relevance_score FLOAT DEFAULT 0.5,
    
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_memories_session_id ON agent_memories(session_id);
CREATE INDEX idx_memories_agent_name ON agent_memories(agent_name);
CREATE INDEX idx_memories_type ON agent_memories(memory_type);

-- 向量索引（用于语义搜索）
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON agent_memories 
USING ivfflat (content_embedding vector_cosine_ops)
WITH (lists = 100);

-- LLM 调用日志表
CREATE TABLE IF NOT EXISTS llm_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id VARCHAR(64) NOT NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    
    model_name VARCHAR(64) NOT NULL,
    model_provider VARCHAR(32) NOT NULL,
    
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    prompt TEXT,
    completion TEXT,
    
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    
    latency_ms INTEGER,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_llm_logs_trace_id ON llm_call_logs(trace_id);
CREATE INDEX idx_llm_logs_task_id ON llm_call_logs(task_id);
CREATE INDEX idx_llm_logs_model ON llm_call_logs(model_name);
CREATE INDEX idx_llm_logs_created_at ON llm_call_logs(created_at);

-- 模型配置表
CREATE TABLE IF NOT EXISTS model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(64) UNIQUE NOT NULL,
    model_provider VARCHAR(32) NOT NULL,
    
    api_key_encrypted TEXT,
    api_base_url VARCHAR(256),
    
    max_tokens INTEGER DEFAULT 4096,
    temperature DECIMAL(3, 2) DEFAULT 0.7,
    
    cost_per_1k_prompt_tokens DECIMAL(10, 6) DEFAULT 0,
    cost_per_1k_completion_tokens DECIMAL(10, 6) DEFAULT 0,
    
    rate_limit_rpm INTEGER DEFAULT 60,
    rate_limit_tpm INTEGER DEFAULT 90000,
    
    is_active BOOLEAN DEFAULT TRUE,
    is_fallback BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 5,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认模型配置
INSERT INTO model_configs (model_name, model_provider, max_tokens, temperature, priority) VALUES
('gpt-4o-mini', 'openai', 16384, 0.7, 1),
('gpt-4o', 'openai', 8192, 0.7, 2),
('gpt-3.5-turbo', 'openai', 4096, 0.7, 3),
('qwen-turbo', 'alibaba', 8192, 0.7, 4),
('glm-4', 'zhipu', 8192, 0.7, 5)
ON CONFLICT (model_name) DO NOTHING;

-- 更新触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_states_updated_at BEFORE UPDATE ON agent_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_model_configs_updated_at BEFORE UPDATE ON model_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
