import pandas as pd
import streamlit as st
import plotly.express as px
from itertools import chain

# 新增全局颜色配置
COLOR_CONFIG = {
    "sidebar_bg": "#2d2d2d",
    "text_color": "white",
    "primary_color": "#00ff9d",
    "grid_color": "rgba(200, 200, 200, 0.2)",
    "hover_bg": "#333333"
}

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
    st.set_page_config(layout="wide", page_title="煤炭质量分析")

    # 动态生成CSS样式
    st.markdown(f"""
    <style>
        :root {{
            --sidebar-bg: {COLOR_CONFIG['sidebar_bg']};
            --text-color: {COLOR_CONFIG['text_color']};
            --primary-color: {COLOR_CONFIG['primary_color']};
            --grid-color: {COLOR_CONFIG['grid_color']};
            --hover-bg: {COLOR_CONFIG['hover_bg']};
        }}

        body {{
            background-color: var(--sidebar-bg);
            color: var(--text-color);
            font-family: Arial, sans-serif;
        }}

        .stApp {{
            background-color: var(--sidebar-bg);
        }}

        /* 侧边栏样式 */
        .sidebar-container .sidebar {{
            background-color: var(--sidebar-bg);
            padding: 1rem;
            border-right: 1px solid var(--primary-color);
        }}

        /* 输入控件样式 */
        input, select, textarea {{
            background: var(--sidebar-bg);
            color: var(--text-color);
            border: 1px solid var(--primary-color);
            padding: 0.5rem;
        }}

        /* 按钮样式 */
        .stButton > button {{
            background: var(--primary-color);
            color: {COLOR_CONFIG['sidebar_bg']};
            border: 1px solid var(--primary-color);
            transition: all 0.3s;
        }}

        .stButton > button:hover {{
            filter: brightness(0.9);
        }}

        /* 数据表格样式 */
        .stDataFrame {{
            background: var(--sidebar-bg);
            color: var(--text-color);
            border: 1px solid var(--primary-color);
        }}

        /* 悬停效果增强 */
        .element-container:hover {{
            background: var(--hover-bg);
            transition: background 0.3s;
        }}
    </style>
    """, unsafe_allow_html=True)

    try:
        # 读取数据
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
            x_col = 'date'
            tickformat = "%m月"
            dtick = "M1"
            grouped = (
                filtered.groupby(group_col)
                .agg({col: 'mean' for col in df.columns[5:12]})
                .reindex(range(1, 13))
                .reset_index()
                .rename(columns={group_col: '月份'})
            )
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
            grouped['date'] = pd.to_datetime(grouped[group_col] + '-01')
            x_col = 'date'
            tickformat = "%Y"
            dtick = "M12"

        # === 可视化优化 ===
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
                )

                # 使用统一颜色配置
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=60),
                    xaxis=dict(
                        title=None,
                        tickformat=tickformat,
                        dtick=dtick,
                        showgrid=False,
                        color=COLOR_CONFIG['text_color'],
                        linecolor=COLOR_CONFIG['primary_color']
                    ),
                    yaxis=dict(
                        range=[grouped[comp].min() * 0.98, grouped[comp].max() * 1.02],
                        showgrid=True,
                        gridcolor=COLOR_CONFIG['grid_color'],
                        color=COLOR_CONFIG['text_color'],
                        linecolor=COLOR_CONFIG['primary_color']
                    ),
                    plot_bgcolor=COLOR_CONFIG['sidebar_bg'],
                    paper_bgcolor=COLOR_CONFIG['sidebar_bg'],
                    font=dict(color=COLOR_CONFIG['text_color']),
                    hovermode="x unified"
                )

                fig.update_traces(
                    line=dict(color=COLOR_CONFIG['primary_color'], width=2),
                    marker=dict(color=COLOR_CONFIG['primary_color'], size=8),
                    hovertemplate=(
                        '<b>%{y:.2f}</b>'
                        '<br>'
                        '%{x|%Y-%m}'
                        '<extra></extra>'
                    )
                )

                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"程序运行错误: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()
