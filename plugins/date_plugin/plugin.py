from plugin_base import PluginBase
import dateparser
from datetime import datetime, timedelta

class Plugin(PluginBase):
    def activate(self):
        print("日期插件已激活")

    def deactivate(self):
        print("日期插件已停用")

    def parse_date_range(self, text):
        """
        解析自然语言日期表达，返回日期范围（开始日期，结束日期）
        支持示例：'上周', '本季度', '昨天', '三天前', '2023年7月' 等
        """
        text = text.strip()

        now = datetime.now()

        # 简单示例实现部分关键字
        if text == "上周":
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            return start.date(), end.date()
        elif text == "本季度":
            quarter = (now.month - 1) // 3 + 1
            start_month = 3 * (quarter - 1) + 1
            start = datetime(now.year, start_month, 1)
            if quarter == 4:
                end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = datetime(now.year, start_month + 3, 1) - timedelta(days=1)
            return start.date(), end.date()
        else:
            # 尝试用dateparser解析单个日期
            dt = dateparser.parse(text)
            if dt:
                return dt.date(), dt.date()
            else:
                return None, None
