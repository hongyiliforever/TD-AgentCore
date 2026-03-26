import configparser
import os
from datetime import datetime, date
from decimal import Decimal
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
    HUI_TABLE_REPORT = cf.get(SECTION_WO, 'hui_table')
except:
    HUI_TABLE_REPORT = "reply_report.tm_agent_report"


class WoOrderDB:
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

    def finish_smart_reply_task(self, begin_time, finish_time, order_id, service_no, agent_output, thinking_process,
                                behavior_context, process_result, remark, model_thinking):
        self._reconnect_if_needed()

        sql = f"""
            INSERT INTO {HUI_TABLE_REPORT} (
                create_time, finish_time, order_id, service_no, agent_output, thinking_process,
                behavior_tree_context, process_result, remark, model_thinking,
                agent_type, process_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '4', '1'
            )
        """

        params = (
            datetime.fromtimestamp(begin_time),
            datetime.fromtimestamp(finish_time),
            str(order_id),
            service_no,
            agent_output,
            thinking_process,
            behavior_context,
            process_result,
            remark,
            model_thinking
        )

        try:
            self.cursor.execute(sql, params)
            self.conn.commit()
            logger.info(f"智能回单结果回写成功: {order_id}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"智能回单结果回写异常 [Order: {order_id}]: {e}")
            logger.error(traceback.format_exc())


def save_smart_reply_result(create_time, finish_time, order_id, service_no, agent_output, thinking_process,
                            behavior_context, process_result, remark, model_thinking):
    db = WoOrderDB()
    try:
        db.finish_smart_reply_task(create_time, finish_time, order_id, service_no, agent_output, thinking_process,
                                   behavior_context, process_result, remark, model_thinking)
    finally:
        db.close()
