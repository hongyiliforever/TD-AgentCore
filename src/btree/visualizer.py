import json
from typing import Any, Dict, List, Optional

from src.btree.behavior_tree import BTreeNode, NodeType, NodeStatus


class BTreeVisualizer:
    NODE_COLORS = {
        NodeType.SEQUENCE: "#2196F3",
        NodeType.SELECTOR: "#FF9800",
        NodeType.ACTION: "#9C27B0",
        NodeType.CONDITION: "#F44336",
        NodeType.PARALLEL: "#00BCD4",
        NodeType.ROOT: "#4CAF50",
    }
    
    STATUS_COLORS = {
        NodeStatus.SUCCESS: "#4CAF50",
        NodeStatus.FAILURE: "#F44336",
        NodeStatus.RUNNING: "#FF9800",
    }
    
    NODE_ICONS = {
        NodeType.SEQUENCE: "➡️",
        NodeType.SELECTOR: "❓",
        NodeType.ACTION: "⚡",
        NodeType.CONDITION: "🔍",
        NodeType.PARALLEL: "⚡⚡",
        NodeType.ROOT: "🏠",
    }
    
    def __init__(self, root: Optional[BTreeNode] = None):
        self.root = root
        self.execution_log: List[Dict[str, Any]] = []
    
    def set_tree(self, root: BTreeNode) -> None:
        self.root = root
    
    def set_execution_log(self, log: List[Dict[str, Any]]) -> None:
        self.execution_log = log
    
    def to_dict(self) -> Dict[str, Any]:
        if not self.root:
            return {}
        return self._node_to_dict(self.root)
    
    def _node_to_dict(self, node: BTreeNode) -> Dict[str, Any]:
        status = self._get_node_status(node.name)
        
        return {
            "name": node.name,
            "title": node.title or node.name,
            "type": node.node_type.value,
            "description": node.description,
            "color": self.NODE_COLORS.get(node.node_type, "#9E9E9E"),
            "status_color": self.STATUS_COLORS.get(status, "#9E9E9E"),
            "status": status.value if status else "pending",
            "icon": self.NODE_ICONS.get(node.node_type, "📦"),
            "func_name": node.func_name,
            "func_type": node.func_type,
            "children": [self._node_to_dict(child) for child in node.children],
        }
    
    def _get_node_status(self, node_name: str) -> Optional[NodeStatus]:
        for log in self.execution_log:
            if log.get("node_name") == node_name:
                status_str = log.get("status")
                if status_str:
                    try:
                        return NodeStatus(status_str)
                    except ValueError:
                        pass
        return None
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def to_mermaid(self) -> str:
        if not self.root:
            return ""
        
        lines = ["graph TD"]
        self._build_mermaid_node(self.root, lines, "")
        return "\n".join(lines)
    
    def _build_mermaid_node(self, node: BTreeNode, lines: List[str], parent_id: str) -> None:
        node_label = f'{node.name}["{self.NODE_ICONS.get(node.node_type, "")} {node.title or node.name}"]'
        node_style = f"style {node.name} fill:{self.NODE_COLORS.get(node.node_type, '#9E9E9E')},color:#fff"
        
        lines.append(f"    {node_label}")
        lines.append(f"    {node_style}")
        
        status = self._get_node_status(node.name)
        if status:
            status_style = f"style {node.name} stroke:{self.STATUS_COLORS.get(status, '#9E9E9E')},stroke-width:4px"
            lines.append(f"    {status_style}")
        
        if parent_id:
            lines.append(f"    {parent_id} --> {node.name}")
        
        for child in node.children:
            self._build_mermaid_node(child, lines, node.name)
    
    def generate_html(self, title: str = "行为树可视化") -> str:
        tree_data = self.to_dict()
        
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        h1 {{ text-align: center; margin-bottom: 30px; font-size: 2em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .legend {{
            display: flex; flex-wrap: wrap; justify-content: center; gap: 15px;
            margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 4px; }}
        .tree-container {{
            background: rgba(255,255,255,0.05); border-radius: 15px;
            padding: 20px; overflow: auto;
        }}
        .node {{ cursor: pointer; }}
        .node rect {{ rx: 8; ry: 8; stroke-width: 2; transition: all 0.3s ease; }}
        .node:hover rect {{ filter: brightness(1.2); stroke-width: 3; }}
        .node text {{ font-size: 12px; fill: #fff; pointer-events: none; }}
        .node-icon {{ font-size: 16px; }}
        .link {{ fill: none; stroke: #666; stroke-width: 2; stroke-opacity: 0.6; }}
        .tooltip {{
            position: absolute; background: rgba(0,0,0,0.9);
            border: 1px solid #444; border-radius: 8px; padding: 12px;
            color: #fff; font-size: 13px; pointer-events: none;
            max-width: 300px; z-index: 1000; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .tooltip h4 {{ margin-bottom: 8px; color: #4CAF50; }}
        .tooltip p {{ margin: 4px 0; }}
        .status-success {{ stroke: #4CAF50 !important; }}
        .status-failure {{ stroke: #F44336 !important; }}
        .status-running {{ stroke: #FF9800 !important; }}
        .controls {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; }}
        .btn {{ padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; transition: all 0.3s ease; }}
        .btn-primary {{ background: #4CAF50; color: white; }}
        .btn-primary:hover {{ background: #45a049; }}
        .btn-secondary {{ background: #2196F3; color: white; }}
        .btn-secondary:hover {{ background: #0b7dda; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌳 {title}</h1>
        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background: #2196F3;"></div><span>Sequence</span></div>
            <div class="legend-item"><div class="legend-color" style="background: #FF9800;"></div><span>Selector</span></div>
            <div class="legend-item"><div class="legend-color" style="background: #9C27B0;"></div><span>Action</span></div>
            <div class="legend-item"><div class="legend-color" style="background: #F44336;"></div><span>Condition</span></div>
            <div class="legend-item"><div class="legend-color" style="background: #00BCD4;"></div><span>Parallel</span></div>
        </div>
        <div class="controls">
            <button class="btn btn-primary" onclick="zoomIn()">🔍+ 放大</button>
            <button class="btn btn-primary" onclick="zoomOut()">🔍- 缩小</button>
            <button class="btn btn-secondary" onclick="resetZoom()">↺ 重置</button>
        </div>
        <div class="tree-container"><svg id="tree-svg"></svg></div>
        <div class="tooltip" id="tooltip" style="display: none;"></div>
    </div>
    <script>
        const treeData = {json.dumps(tree_data, ensure_ascii=False)};
        let currentZoom = 1;
        let svg, g, zoom;
        
        function initTree() {{
            const container = document.querySelector('.tree-container');
            const width = container.clientWidth - 40;
            const height = 600;
            
            svg = d3.select('#tree-svg').attr('width', width).attr('height', height);
            zoom = d3.zoom().scaleExtent([0.1, 3]).on('zoom', (event) => {{ g.attr('transform', event.transform); }});
            svg.call(zoom);
            g = svg.append('g');
            
            if (treeData && treeData.name) {{
                const root = d3.hierarchy(treeData);
                const treeLayout = d3.tree().nodeSize([180, 120]);
                treeLayout(root);
                
                const minX = d3.min(root.descendants(), d => d.x);
                const maxX = d3.max(root.descendants(), d => d.x);
                const minY = d3.min(root.descendants(), d => d.y);
                const maxY = d3.max(root.descendants(), d => d.y);
                
                const treeWidth = maxX - minX + 200;
                const treeHeight = maxY - minY + 100;
                
                svg.attr('width', Math.max(width, treeWidth));
                svg.attr('height', Math.max(height, treeHeight));
                
                const offsetX = -minX + 100;
                const offsetY = 50;
                
                g.selectAll('.link')
                    .data(root.links())
                    .enter()
                    .append('path')
                    .attr('class', 'link')
                    .attr('d', d3.linkVertical().x(d => d.x + offsetX).y(d => d.y + offsetY));
                
                const nodes = g.selectAll('.node')
                    .data(root.descendants())
                    .enter()
                    .append('g')
                    .attr('class', 'node')
                    .attr('transform', d => `translate(${{d.x + offsetX}},${{d.y + offsetY}})`);
                
                nodes.append('rect')
                    .attr('x', -80).attr('y', -25)
                    .attr('width', 160).attr('height', 50)
                    .attr('fill', d => d.data.color || '#9E9E9E')
                    .attr('stroke', d => d.data.status_color || '#fff')
                    .attr('stroke-width', d => d.data.status !== 'pending' ? 3 : 1);
                
                nodes.append('text').attr('dy', -5).attr('text-anchor', 'middle').text(d => d.data.icon || '').attr('class', 'node-icon');
                nodes.append('text').attr('dy', 12).attr('text-anchor', 'middle').text(d => d.data.title || d.data.name);
                nodes.on('mouseover', showTooltip).on('mouseout', hideTooltip);
            }}
        }}
        
        function showTooltip(event, d) {{
            const tooltip = document.getElementById('tooltip');
            let content = `<h4>${{d.data.icon}} ${{d.data.title || d.data.name}}</h4>`;
            content += `<p><strong>名称:</strong> ${{d.data.name}}</p>`;
            content += `<p><strong>类型:</strong> ${{d.data.type}}</p>`;
            content += `<p><strong>状态:</strong> ${{d.data.status}}</p>`;
            if (d.data.description) content += `<p><strong>描述:</strong> ${{d.data.description}}</p>`;
            if (d.data.func_name) content += `<p><strong>函数:</strong> ${{d.data.func_name}}</p>`;
            tooltip.innerHTML = content;
            tooltip.style.display = 'block';
            tooltip.style.left = (event.pageX + 15) + 'px';
            tooltip.style.top = (event.pageY - 10) + 'px';
        }}
        
        function hideTooltip() {{ document.getElementById('tooltip').style.display = 'none'; }}
        function zoomIn() {{ currentZoom = Math.min(currentZoom * 1.2, 3); svg.transition().duration(300).call(zoom.scaleTo, currentZoom); }}
        function zoomOut() {{ currentZoom = Math.max(currentZoom / 1.2, 0.1); svg.transition().duration(300).call(zoom.scaleTo, currentZoom); }}
        function resetZoom() {{ currentZoom = 1; svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity); }}
        
        document.addEventListener('DOMContentLoaded', initTree);
        window.addEventListener('resize', initTree);
    </script>
</body>
</html>'''
    
    def save_html(self, file_path: str, title: str = "行为树可视化") -> None:
        import os
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        html_content = self.generate_html(title)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
