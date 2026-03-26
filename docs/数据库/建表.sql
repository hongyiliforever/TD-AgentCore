CREATE TABLE wo_order.js_order_check_agent_output (
  order_id VARCHAR(64) NOT NULL,                  -- 系统内部唯一标识，主键
  service_no VARCHAR(64),                         -- 工单号/客服等外部流水号
  agent_type VARCHAR(20),                         -- 智能体类型（1容量 2投诉处理 3质检 4预处理）
  thinking_process TEXT,                          -- 思考过程(SAIDA)
  model_thinking TEXT,                            -- 大模型思考过程
  agent_output TEXT,                              -- 智能体输出结果
  behavior_tree_context TEXT,                     -- 行为树上下文
  process_status VARCHAR(20),                     -- 处理状态
  process_result VARCHAR(20),                     -- 处理结果
  create_time TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP, -- 创建时间
  finish_time TIMESTAMP(0),                       -- 智能体处理结束时间
  remark TEXT,                                    -- 备注
  CONSTRAINT pk_tm_agent_report PRIMARY KEY (order_id)
);

COMMENT ON TABLE tm_agent_report IS '智能体结果表';
