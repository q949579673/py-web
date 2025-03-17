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
            df = df[df.iloc[:, 4].str.startswith('原料.煤炭.炼焦煤', na=False)]
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)

    except Exception as e:
        st.error(f"数据加载失败，请检查网络连接或数据文件: {str(e)}")
        st.stop()

def main():
    # 修正点1：set_page_config的参数对齐
    st.set_page_config(
        layout="wide",  # 缩进4空格
        page_title="煤炭质量分析",
        page_icon="🧊",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://example.com',
            'Report a bug': "https://example.com",
            'About': "# 煤炭质量分析系统"
        }
    )  # 闭合括号对齐

    # 自定义深色主题样式
    st.markdown("""
    <style>
        /* 主容器背景 */
        .stApp > div {
            background-color: #2d2d2d;
        }
        /* 侧边栏主背景 */
        [data-testid="stSidebar"] > div:first-child {
            background-color: #2d2d2d !important;
        }
        /* 其他样式保持原样... */
    </style>
    """, unsafe_allow_html=True)

    try:  # 修正点2：try语句与st.markdown对齐
        # 读取数据
        df = load_all_sheets_from_github()

        # === 日期处理 ===
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
                    template="plotly_dark",
                )

                line_color = '#00ff9d'
                grid_color = 'rgba(200, 200, 200, 0.2)'

                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=60),
                    xaxis=dict(
                        title=None,
                        tickformat=tickformat,
                        dtick=dtick,
                        tickangle=0,
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
                    hovertemplate=(
                        '<b>%{y:.2f}</b>'
                        '<br>'
                        '%{x|%Y-%m}'
                        '<extra></extra>'
                    )
                )

                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:  # 修正点3：except与try对齐
        st.error(f"程序运行错误: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()
