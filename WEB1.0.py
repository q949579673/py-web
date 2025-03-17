import pandas as pd
import streamlit as st
import plotly.express as px
from itertools import chain


# 新增函数：从GitHub加载数据
def load_all_sheets_from_github():
    """从GitHub仓库读取Excel数据"""
    GITHUB_RAW_URL = "https://github.com/q949579673/py-web/raw/refs/heads/main/2022-2024%E5%B9%B4%E8%BF%9B%E5%8E%82%E7%82%BC%E7%84%A6%E7%85%A4%E8%B4%A8%E9%87%8F%E6%8C%87%E6%A0%87%E7%BB%9F%E8%AE%A1(2).xlsx"
    try:
        xls = pd.ExcelFile(GITHUB_RAW_URL, engine='openpyxl')
        sheet_names = xls.sheet_names

        dfs = []
        for sheet in sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df = df[df.iloc[:, 4].str.startswith('原料.煤炭.炼焦煤', na=False)]
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)

    except Exception as e:
        st.error(f"数据加载失败，请检查网络连接或数据文件: {str(e)}")
        st.stop()



def main():
    st.markdown("""
<style>
    /* 强制所有元素使用深色主题 */
    body, .stApp, .stDataFrame, .stPlotlyChart {
        color: white !important;
        background-color: #2d2d2d !important;
    }

    /* 输入控件深度覆盖 */
    .st-bw, .st-cm, .st-dh, .stSelectbox, .stTextInput {
        background: #333 !important;
        color: white !important;
        border-color: #444 !important;
    }

    /* 表格单元格深度覆盖 */
    .dataframe th, .dataframe td {
        background-color: #333 !important;
        color: white !important;
        border-color: #444 !important;
    }

    /* 滑块控件样式 */
    .stSlider .thumb {
        background-color: #00ff9d !important;
    }
    .stSlider .track {
        background-color: #444 !important;
    }

    /* 多选控件样式 */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #444 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

    try:
        # 读取数据
        df = load_all_sheets_from_github()  # 替换为GitHub数据加载

        # === 日期处理修复 ===
        df['月份'] = (
            df['月份']
            .astype(str)
            .str.replace(r'[^0-9]', '', regex=True)
            .str[:6]
            .pipe(lambda s: pd.to_datetime(s, format='%Y%m', errors='coerce'))
        )

        df = df.dropna(subset=['月份']).copy()
        df = df[df['月份'].dt.day == 1]

        df['年份'] = df['月份'].dt.year
        df['月份序号'] = df['月份'].dt.month
        df['年月'] = df['月份'].dt.strftime('%Y-%m')

        # === 侧边栏控件 ===
        st.sidebar.header("分析条件设置")

        unique_items = df.iloc[:, 4].unique()
        selected_item = st.sidebar.selectbox(
            "选择ITEM类型",
            unique_items,
            help="支持输入文字快速筛选"
        )

        year_options = sorted(df['年份'].unique())
        year_options.insert(0, 'all')
        selected_year = st.sidebar.selectbox(
            "选择分析范围",
            options=year_options,
            format_func=lambda x: '检索ITEM所有日期数据' if x == 'all' else x,
            index=0
        )

        # === 数据过滤和聚合 ===
        filtered = df[df.iloc[:, 4] == selected_item]

        if selected_year != 'all':
            filtered = filtered[filtered['年份'] == selected_year]
            group_col = '月份序号'
            x_col = 'date'  # 改为统一的日期字段
            tickformat = "%m月"
            dtick = "M1"
            grouped = (
                filtered.groupby(group_col)
                .agg({col: 'mean' for col in df.columns[5:12]})
                .reindex(range(1, 13))
                .reset_index()
                .rename(columns={group_col: '月份'})
            )
            # 添加日期列（重要修改）
            grouped['date'] = pd.to_datetime(
                str(selected_year) + '-' + grouped['月份'].astype(str) + '-01'
            )
        else:
            group_col = '年月'
            grouped = (
                filtered.groupby(group_col)
                .agg({col: 'mean' for col in df.columns[5:12]})
                .reset_index()
                .sort_values(group_col)
            )
            # 添加日期列并转换为时间格式
            grouped['date'] = pd.to_datetime(grouped[group_col] + '-01')
            x_col = 'date'
            tickformat = "%Y"
            dtick = "M12"

        # === 可视化调整 ===
        st.title(f"{selected_item}质量趋势分析" + (f" - {selected_year}年" if selected_year != 'all' else ""))

        cols = chain(*[st.columns(2) for _ in range(4)])

        for idx, comp in enumerate(df.columns[5:12]):
            if idx >= 7:
                break

            with next(cols):
                fig = px.line(
                    grouped,
                    x=x_col,
                    y=comp,
                    title=f"{comp}趋势",
                    markers=True,
                    height=300,
                    template="plotly_dark",  # 使用深色模板
                )

                # 统一颜色方案
                line_color = '#00ff9d'  # 荧光绿提高对比度
                grid_color = 'rgba(200, 200, 200, 0.2)'

                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=60),
                    xaxis=dict(
                        title=None,
                        tickformat=tickformat,
                        dtick=dtick,
                        tickangle=0 if selected_year == 'all' else 0,
                        showgrid=False,
                        color='white'
                    ),
                    yaxis=dict(
                        range=[grouped[comp].min() * 0.98, grouped[comp].max() * 1.02],
                        showgrid=True,
                        gridcolor=grid_color,
                        color='white'
                    ),
                    plot_bgcolor='rgba(0, 0, 0, 0)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    font=dict(color='white'),
                    hovermode="x unified"
                )

                fig.update_traces(
                    line=dict(color=line_color, width=2),
                    marker=dict(color=line_color, size=8),
                    # 修改悬停模板为数值+日期双行显示
                    hovertemplate=(
                        '<b>%{y:.2f}</b>'  # 第一行加粗显示数值（保留两位小数）
                        '<br>'  # 换行符
                        '%{x|%Y-%m}'  # 第二行显示完整年月
                        '<extra></extra>'  # 隐藏默认系列名称
                    )
                )

                st.plotly_chart(fig, use_container_width=True)
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=60),
            xaxis=dict(
                title=None,
                tickformat=tickformat,
                dtick=dtick,
                tickangle=0,  # 统一设置为0度旋转
                showgrid=False,
                color='white'
            ),
            yaxis=dict(
                range=[grouped[comp].min() * 0.98, grouped[comp].max() * 1.02],
                showgrid=True,
                gridcolor=grid_color,
                color='white'
            ),
            # ... 其他保持不变的布局设置
        )

    except Exception as e:
        st.error(f"程序运行错误: {str(e)}")
        st.stop()


if __name__ == "__main__":
    main()
