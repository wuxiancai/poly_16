import csv
import os
import re
import shutil
from datetime import datetime


class _SimpleLogger:
    def info(self, msg):
        print(msg)
    def warning(self, msg):
        print(msg)
    def error(self, msg):
        print(msg)


def repair_csv_file(csv_file, logger=None):
    """修复损坏的CSV文件,移除无效行并重建文件。
    参数:
    - csv_file: CSV 文件路径
    - logger: 可选的日志记录器,需支持 info/warning/error 方法
    """
    logger = logger or _SimpleLogger()

    if not os.path.exists(csv_file):
        logger.info("CSV文件不存在,无需修复")
        return

    standardized_flag_file = f"{csv_file}.standardized"
    if os.path.exists(standardized_flag_file):
        csv_mtime = os.path.getmtime(csv_file)
        flag_mtime = os.path.getmtime(standardized_flag_file)
        if csv_mtime <= flag_mtime:
            logger.info("CSV文件已标准化,跳过检查")
            return
        else:
            logger.info("CSV文件已更新,重新检查格式")

    valid_rows = []
    invalid_rows = []
    has_format_changes = False

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            line_number = 0
            for row in reader:
                line_number += 1
                try:
                    if len(row) >= 4:
                        original_date_str = row[0].strip()
                        date_str = original_date_str
                        cash = float(row[1].strip())
                        profit = float(row[2].strip())

                        profit_rate_str = row[3].strip()
                        if re.search(r'\d{4}-\d{2}-\d{2}', profit_rate_str):
                            match = re.match(r'([\d\.%\-]+)(\d{4}-\d{2}-\d{2}.*)', profit_rate_str)
                            if match:
                                profit_rate_str = match.group(1)
                                logger.warning(
                                    f"第{line_number}行利润率字段包含日期信息,已分离: '{row[3]}' -> '{profit_rate_str}'"
                                )
                                has_format_changes = True

                        if profit_rate_str.endswith('%'):
                            profit_rate = float(profit_rate_str.rstrip('%')) / 100
                        else:
                            profit_rate = float(profit_rate_str)

                        # 日期格式标准化
                        try:
                            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                        except ValueError:
                            try:
                                parsed_date = datetime.strptime(date_str, '%Y/%m/%d')
                                date_str = parsed_date.strftime('%Y-%m-%d')
                                logger.info(
                                    f"第{line_number}行日期格式已标准化: '{original_date_str}' -> '{date_str}'"
                                )
                                has_format_changes = True
                            except ValueError:
                                try:
                                    parsed_date = datetime.strptime(date_str, '%Y/%#m/%#d')
                                    date_str = parsed_date.strftime('%Y-%m-%d')
                                    logger.info(
                                        f"第{line_number}行日期格式已标准化: '{original_date_str}' -> '{date_str}'"
                                    )
                                    has_format_changes = True
                                except ValueError:
                                    raise ValueError(f"日期格式不支持: {date_str}")

                        if len(row) >= 6:
                            total_profit = float(row[4].strip())
                            total_profit_rate_str = row[5].strip()
                            if re.search(r'\d{4}-\d{2}-\d{2}', total_profit_rate_str):
                                match = re.match(r'([\d\.%\-]+)(\d{4}-\d{2}-\d{2}.*)', total_profit_rate_str)
                                if match:
                                    total_profit_rate_str = match.group(1)
                                    logger.warning(
                                        f"第{line_number}行总利润率字段包含日期信息,已分离: '{row[5]}' -> '{total_profit_rate_str}'"
                                    )
                                    has_format_changes = True

                            if total_profit_rate_str.endswith('%'):
                                total_profit_rate = float(total_profit_rate_str.rstrip('%')) / 100
                            else:
                                total_profit_rate = float(total_profit_rate_str)

                        fixed_row = [
                            date_str,
                            f"{cash:.2f}",
                            f"{profit:.2f}",
                            f"{profit_rate*100:.2f}%",
                        ]
                        if len(row) >= 6:
                            fixed_row.extend([f"{total_profit:.2f}", f"{total_profit_rate*100:.2f}%"])
                        if len(row) >= 7:
                            fixed_row.append(row[6].strip())

                        valid_rows.append(fixed_row)
                    else:
                        invalid_rows.append((line_number, row, "列数不足"))
                except Exception as e:
                    invalid_rows.append((line_number, row, str(e)))

        if invalid_rows or has_format_changes:
            backup_file = f"{csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(csv_file, backup_file)

            if invalid_rows:
                logger.info(f"发现{len(invalid_rows)}行无效数据,已创建备份: {backup_file}")
                for line_num, row, error in invalid_rows:
                    logger.warning(f"移除第{line_num}行无效数据: {row} - {error}")

            if has_format_changes:
                logger.info(f"发现格式需要标准化,已创建备份: {backup_file}")

            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(valid_rows)

            if invalid_rows and has_format_changes:
                logger.info(f"CSV文件修复和格式标准化完成,保留{len(valid_rows)}行有效数据")
            elif invalid_rows:
                logger.info(f"CSV文件修复完成,保留{len(valid_rows)}行有效数据")
            elif has_format_changes:
                logger.info(f"CSV文件格式标准化完成,处理{len(valid_rows)}行数据")

            try:
                with open(standardized_flag_file, 'w', encoding='utf-8') as flag_file:
                    flag_file.write(
                        f"CSV文件已于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 标准化"
                    )
                logger.info(f"已创建标准化标记文件: {standardized_flag_file}")
            except Exception as flag_error:
                logger.warning(f"创建标准化标记文件失败: {flag_error}")
        else:
            logger.info("CSV文件检查完成,未发现无效数据或格式问题")
            try:
                with open(standardized_flag_file, 'w', encoding='utf-8') as flag_file:
                    flag_file.write(
                        f"CSV文件已于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 检查,无需标准化"
                    )
            except Exception as flag_error:
                logger.warning(f"创建标准化标记文件失败: {flag_error}")

    except Exception as e:
        logger.error(f"CSV文件修复失败: {e}")