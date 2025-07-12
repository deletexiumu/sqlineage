-- ① 业务日期：今天 → 20250626
-- ② 开启动态分区（如已全局开启，可省略）
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

-- 1.大幅提高每个Map任务处理的数据量下限
SET tez.grouping.min-size=10737418240;
-- 10 GB
-- 2. 大幅提高每个Map任务处理的数据量上限
SET tez.grouping.max-size=21474836480;
-- 20 GB
-- 3. 增加每个Reducer处理的数据量来减少Reducer数量
SET hive.exec.reducers.bytes.per.reducer=10737418240;
-- 10 GB
-- 4. 【强制指定】直接设定Reduce任务的最大数量
SET hive.exec.reducers.max=64;


CREATE TABLE if not exists dwt_capital.dim_investment_event_df
(
    `bk_investment_event_id`           STRING COMMENT '主键-投资事件ID;同要素库logic_id',
    `sk_investment_event_id`           BIGINT COMMENT '代理键-投资事件ID;对要素库logic_id进行xxhash计算',
    `investment_event_name`            STRING COMMENT '投资事件名称',
    `project_operational_status`       STRING COMMENT '项目运营状态',
    `news_source`                      STRING COMMENT '新闻来源',
    `news_source_link`                 STRING COMMENT '新闻来源链接',
    `news_title`                       STRING COMMENT '新闻标题',
    `release_time`                     timestamp COMMENT '发布时间',
    `news_details`                     STRING COMMENT '新闻详情',
    `transferred_share_capital_number` decimal(18, 2) COMMENT '出让股本数',
    `valuation`                        decimal(18, 2) COMMENT '估值',
    `create_time`                      timestamp COMMENT '数据创建时间',
    `update_time`                      timestamp COMMENT '数据更新时间'
) COMMENT '维度表-投资事件'
PARTITIONED BY ( `dt` string COMMENT '分区列-日期,yyyyMMdd')
stored as orc
tblproperties (
    'orc.compress' = 'zlib'
    )
;

insert overwrite table dwt_capital.dim_investment_event_df partition (dt = '20250625')
select logic_id                         as bk_investment_event_id,
       shared_udf_prod.xxhash(logic_id) as sk_investment_event_id,
       investment_event_name            as investment_event_name,
       project_operational_status       as project_operational_status,
       news_source                      as news_source,
       news_source_link                 as news_source_link,
       news_title                       as news_title,
       release_time                     as release_time,
       news_details                     AS news_details,
       transferred_share_capital_number AS transferred_share_capital_number,
       valuation                        AS valuation,
       `current_timestamp`()            as create_time,
       `current_timestamp`()            as update_time
from dwd_zbk.dwd_zbk_investor_project_information
;