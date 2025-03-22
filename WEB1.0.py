import pandas as pd
import streamlit as st
import plotly.express as px
from itertools import chain


def load_all_sheets_from_github():
    """从GitHub仓库读取Excel数据"""
    GITHUB_RAW_URL = "https://github.com/q949579673/py-web/raw/refs/heads/main/2022-2024%E5%B9%B4%E8%BF%9B%E5%8E%82%E7%82%BC%E7%84%A6%E7%85%A4%E8%B4%A8%E9%87%8F%E6%8C%87%E6%A0%87%E7%BB%9F%E8%AE%A1(2).xlsx"
    try:
        xls = pd.ExcelFile(GITHUB_RAW_URL, engine='openpyxl')
        sheet_names = xls.sheet_names

        dfs = []
        for sheet in sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            mask = (
                    df.iloc[:, 4].str.contains('煤', na=False, regex=True)  # 按实际关键词修改
                    & ~df.iloc[:, 4].str.startswith('日期')  # 排除可能的异常记录
            )
            df = df[mask]
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)
    
    
    except Exception as e:  # ✅ 添加异常处理
        st.error(f"数据加载失败: {str(e)}")
        return pd.DataFrame()  # 返回空DataFrame保持程序运行


def main():
    st.set_page_config(layout="wide", page_title="煤炭质量分析")
    # 强制深色模式设置
    st.markdown("""
        <meta name="color-scheme" content="only dark">
        <meta name="theme-color" content="#2d2d2d">
    """, unsafe_allow_html=True)

    # 自定义CSS样式
    st.markdown("""
    <style>
        :root {
            color-scheme: only dark !important;
            --sidebar-bg: #1a1a1a;
            --text-color: #ffffff;
            --primary-color: #00ff9d;
        }

        /* 全局文字颜色 */
        body, .stApp, .stMarkdown, 
        .stDataFrame, .stButton > button,
        .stSidebarHeader, .stSelectbox label,
        .stNumberInput label, .stTitle {
            color: white !important;
        }

        /* 侧边栏文字 */
        [data-testid="stSidebar"] *:not([data-baseweb="select"] *) {
            color: white !important;
        }

        /* 表格文字 */
        .stDataFrame td, .stDataFrame th {
            color: white !important;
        }

        /* 下拉框深度样式修正 */
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] input {
            color: black !important;
            background-color: white !important;
        }

        /* 下拉菜单选项 */
        div[role="listbox"] div {
            color: black !important;
            background: white !important;
        }

        /* 输入框聚焦状态 */
        div[data-baseweb="select"] input:focus {
            background-color: white !important;
            color: black !important;
        }

        /* 选项悬停效果 */
        div[role="option"]:hover {
            background-color: #f0f0f0 !important;
        }

        /* 背景设置 */
        html, body, .stApp {
            background-color: var(--sidebar-bg) !important;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--sidebar-bg), #121212) !important;
            border-right: 1px solid #404040 !important;
        }

        /* 输入控件 */
        .stTextInput input, .stTextArea textarea {
            background: #333 !important;
            border: 1px solid #555 !important;
        }

        /* 按钮样式 */
        .stButton {
            background: #007bff !important;
        }

        /* 图表容器 */
        .stPlotlyChart {
            background: #333;
            border: 1px solid #444;
            padding: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    try:
        # 数据加载和处理
        df = load_all_sheets_from_github()

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
