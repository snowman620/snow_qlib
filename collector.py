import tushare as ts
import pandas as pd
import os
import time
import logging
from datetime import datetime, timedelta


class TushareSHDailyDownloaderPro:

    def __init__(
        self,
        token: str,
        output_dir: str = "raw_csv",
        log_dir: str = "logs",
        start_date: str = "20250101",
        end_date: str = None,
        sleep_seconds: float = 1.2,
        retry_times: int = 3
    ):

        ts.set_token(token)
        self.pro = ts.pro_api()

        self.output_dir = output_dir
        self.log_dir = log_dir
        self.start_date = start_date
        self.end_date = end_date
        self.sleep_seconds = sleep_seconds
        self.retry_times = retry_times

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

        self._init_logger()
        self.failed_stocks = []

    # ------------------------------------------------
    # 初始化日志
    # ------------------------------------------------
    def _init_logger(self):

        log_file = os.path.join(
            self.log_dir,
            f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.logger = logging.getLogger()

    # ------------------------------------------------
    # 获取 SH 股票列表
    # ------------------------------------------------
    def get_stock_list(self):

        csv_file = os.path.join(self.output_dir, "stock_basic_full.csv")

        try:
            print("尝试从 Tushare 获取股票列表...")
            self.logger.info("开始调用 stock_basic 接口")

            df = self.pro.stock_basic(
                exchange='SSE',
                list_status='L,D,P'
            )

            if df.empty:
                raise Exception("接口返回空数据")

            # 保存到本地
            df.to_csv(csv_file, index=False, encoding="utf-8-sig")

            print("接口获取成功，已更新本地 CSV")
            self.logger.info(f"接口成功，股票数量: {len(df)}")

            return df

        except Exception as e:

            print("接口调用失败，尝试从本地 CSV 读取...")
            self.logger.error(f"接口失败: {e}")

            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                self.logger.info("使用本地 CSV 股票列表")
                return df
            else:
                self.logger.critical("本地 CSV 不存在，无法继续")
                raise Exception("stock_basic 接口失败，且本地 CSV 不存在")


    # ------------------------------------------------
    # 获取最后日期（增量）
    # ------------------------------------------------
    def get_last_date(self, file_path):

        if not os.path.exists(file_path):
            return None

        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return None
            last_date = df["date"].max()
            return datetime.strptime(last_date, "%Y-%m-%d")
        except:
            return None

    # ------------------------------------------------
    # 下载单个股票
    # ------------------------------------------------
    def download_one(self, ts_code):

        file_code = ts_code.split('.')[1] + ts_code.split('.')[0]
        file_path = os.path.join(self.output_dir, f"{file_code}.csv")

        last_date = self.get_last_date(file_path)

        if last_date:
            start_date = (last_date + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start_date = self.start_date

        end_date = self.end_date or datetime.now().strftime("%Y%m%d")

        if start_date > end_date:
            print(f"{file_code} 已最新")
            return

        for attempt in range(self.retry_times):

            try:
                df = self.pro.daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )

                if df.empty:
                    print(f"{file_code} 无新数据")
                    return

                df["date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
                df = df.sort_values("date")

                df_out = df[[
                    "date", "open", "high",
                    "low", "close", "vol", "amount"
                ]].copy()

                df_out.rename(columns={"vol": "volume"}, inplace=True)

                if os.path.exists(file_path):
                    df_out.to_csv(file_path, mode='a', header=False, index=False)
                else:
                    df_out.to_csv(file_path, index=False)

                print(f"{file_code} 更新完成")
                self.logger.info(f"{file_code} 成功")
                break

            except Exception as e:

                self.logger.error(f"{file_code} 第{attempt+1}次失败: {e}")
                time.sleep(3)

                if attempt == self.retry_times - 1:
                    self.failed_stocks.append(file_code)

        time.sleep(self.sleep_seconds)

    # ------------------------------------------------
    # 主程序
    # ------------------------------------------------
    def run(self):

        stock_df = self.get_stock_list()
        total = len(stock_df)

        start_time = time.time()

        for i, ts_code in enumerate(stock_df["ts_code"]):

            print(f"\n({i+1}/{total}) 处理 {ts_code}")

            self.download_one(ts_code)

            # 估算剩余时间
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            remaining = avg_time * (total - i - 1)

            print(f"预计剩余时间: {remaining/60:.1f} 分钟")

        # 写入失败股票
        if self.failed_stocks:
            failed_file = os.path.join(self.log_dir, "failed_stocks.txt")
            with open(failed_file, "w") as f:
                for code in self.failed_stocks:
                    f.write(code + "\n")

            print(f"\n失败股票已记录到: {failed_file}")
            self.logger.warning(f"失败股票数量: {len(self.failed_stocks)}")

        print("\n全部 SH 下载完成")
        self.logger.info("全部下载完成")


if __name__ == "__main__":
    downloader = TushareSHDailyDownloaderPro(
        token="0d3212df3fce430d282ef70cdfd4cf693e07f29a5b4895dde8d3e579",
        output_dir="./data/raw_csv",
        log_dir="./logs",
        start_date="20210101",
        sleep_seconds=1.5
    )
    downloader.run()
