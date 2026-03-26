import configparser
import os
from datetime import datetime
import psycopg2
from an_copilot.framework.logging import an_logger as logger
import traceback

cf = configparser.ConfigParser()
file = os.path.join(os.path.dirname(__file__), "../../config/db_config.txt")
cf.read(file, encoding='utf-8')

SECTION_WO = 'wo_agent_pgsql'
host = cf.get(SECTION_WO, 'host')
port = cf.getint(SECTION_WO, 'port')
user = cf.get(SECTION_WO, 'user')
passwd = cf.get(SECTION_WO, 'passwd')
db_name = cf.get(SECTION_WO, 'db_name')

try:
    QUALITY_DEFECT_TABLE = cf.get(SECTION_WO, 'quality_defect_table')
except:
    QUALITY_DEFECT_TABLE = "wo_order.js_order_check_agent_output"


class QualityDefectDB:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg2.connect(host=host, port=port, user=user, password=passwd, database=db_name)
            self.cursor = self.conn.cursor()
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def _reconnect_if_needed(self):
        if self.conn is None or self.conn.closed != 0:
            logger.info("数据库连接已断开，尝试重连...")
            self.connect()

    def save_agent_output(self, order_id: str, agent_output: str):
        """
        保存智能体输出（节点①使用，覆盖写入）
        
        执行 SQL: UPDATE ... SET agent_output = '拼接好的Markdown1' WHERE ...
        """
        self._reconnect_if_needed()
        
        sql = f"""
            UPDATE {QUALITY_DEFECT_TABLE}
            SET agent_output = %s, update_time = %s
            WHERE order_id = %s
        """
        
        params = (
            agent_output,
            datetime.now(),
            str(order_id),
        )
        
        try:
            self.cursor.execute(sql, params)
            row_count = self.cursor.rowcount
            
            if row_count == 0:
                insert_sql = f"""
                    INSERT INTO {QUALITY_DEFECT_TABLE} (
                        order_id, agent_output, create_time, update_time
                    ) VALUES (%s, %s, %s, %s)
                """
                self.cursor.execute(insert_sql, (str(order_id), agent_output, datetime.now(), datetime.now()))
                logger.info(f"质差定界结果插入成功: {order_id}")
            else:
                logger.info(f"质差定界结果更新成功: {order_id}")
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"质差定界结果保存异常 [Order: {order_id}]: {e}")
            logger.error(traceback.format_exc())

    def append_agent_output(self, order_id: str, agent_output: str):
        """
        追加智能体输出（节点②、③使用，追加写入）
        
        执行 SQL: UPDATE ... SET agent_output = CONCAT(agent_output, '\n\n', '拼接好的Markdown') WHERE ...
        """
        self._reconnect_if_needed()
        
        sql = f"""
            UPDATE {QUALITY_DEFECT_TABLE}
            SET agent_output = CONCAT(COALESCE(agent_output, ''), %s, %s),
                update_time = %s
            WHERE order_id = %s
        """
        
        params = (
            '\n\n',
            agent_output,
            datetime.now(),
            str(order_id),
        )
        
        try:
            self.cursor.execute(sql, params)
            row_count = self.cursor.rowcount
            
            if row_count == 0:
                logger.warning(f"追加质差定界结果失败，记录不存在: {order_id}")
            else:
                logger.info(f"质差定界结果追加成功: {order_id}")
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"质差定界结果追加异常 [Order: {order_id}]: {e}")
            logger.error(traceback.format_exc())

    def get_agent_output(self, order_id: str) -> str:
        """
        获取智能体输出
        """
        self._reconnect_if_needed()
        
        sql = f"""
            SELECT agent_output FROM {QUALITY_DEFECT_TABLE}
            WHERE order_id = %s
        """
        
        try:
            self.cursor.execute(sql, (str(order_id),))
            result = self.cursor.fetchone()
            if result:
                return result[0] or ''
            return ''
        except Exception as e:
            logger.error(f"获取质差定界结果异常 [Order: {order_id}]: {e}")
            return ''


def save_quality_defect_output(order_id: str, agent_output: str):
    """
    保存质差定界智能体输出（覆盖写入）
    
    用于节点①：质差识别检测
    """
    db = QualityDefectDB()
    try:
        db.save_agent_output(order_id, agent_output)
    finally:
        db.close()


def append_quality_defect_output(order_id: str, agent_output: str):
    """
    追加质差定界智能体输出
    
    用于节点②、③：预警聚合、定界定位
    """
    db = QualityDefectDB()
    try:
        db.append_agent_output(order_id, agent_output)
    finally:
        db.close()


def get_quality_defect_output(order_id: str) -> str:
    """
    获取质差定界智能体输出
    """
    db = QualityDefectDB()
    try:
        return db.get_agent_output(order_id)
    finally:
        db.close()
