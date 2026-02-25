#!/usr/bin/env python
# coding: utf-8
# author: snowman

import os
import qlib
from qlib.data import D
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.strategy import TopkDropoutStrategy
from qlib.contrib.evaluate import backtest_daily
from qlib.data.dataset import DatasetH

########################################
# 初始化
########################################

# 防止 mlflow 自动启动
os.environ["DISABLE_MLFLOW"] = "1"
os.environ.pop("MLFLOW_TRACKING_URI", None)

qlib.init(provider_uri="./data/qlib_data")

########################################
# 获取股票
########################################

inst_dict = D.list_instruments(D.instruments("all"))
inst_list = list(inst_dict.keys())

########################################
# 构建数据集
########################################

handler = {
    "class": "Alpha158",
    "module_path": "qlib.contrib.data.handler",
    "kwargs": {
        "start_time": "2021-01-01",
        "end_time": "2026-02-24",
        "instruments": inst_list,
    },
}

dataset = DatasetH(
    handler=handler,
    segments={
        "train": ("2021-01-01", "2023-12-31"),
        "test": ("2024-01-01", "2026-02-24"),
    },
)

########################################
# 训练
########################################

model = LGBModel()
model.fit(dataset)

########################################
# 预测
########################################

pred = model.predict(dataset, segment="test")

########################################
# 回测
########################################

strategy = TopkDropoutStrategy(topk=20, n_drop=5)

report, _ = backtest_daily(
    start_time="2024-01-01",
    end_time="2026-02-24",
    strategy=strategy,
    signal=pred,
)

print(report.tail())
