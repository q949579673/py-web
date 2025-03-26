import pandas as pd
import streamlit as st
import plotly.express as px
from itertools import chain


def load_all_sheets_from_github():
    """从GitHub仓库读取Excel数据"""
    GITHUB_RAW_URL = "https://github.com/q949579673/py-web/raw/refs/heads/main/%E8%BF%9B%E5%8E%82%E7%82%BC%E7%84%A6%E7%85%A4%E8%B4%A8%E9%87%8F%E6%8C%87%E6%A0%87%E7%BB%9F%E8%AE%A1%E5%BA%93.xlsx"
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
        # 处理B列原始日期（精确到日）
        df['原始日期'] = (
            df.iloc[:, 1].astype(str)  # 假设B列是第2列
            .str.replace(r'[^0-9]', '', regex=True)  # 去除非数字字符
            .str[:8]  # 取前8位数字
            .pipe(lambda s: pd.to_datetime(s, format='%Y%m%d', errors='coerce'))
        )

        # 处理C列月份
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

        # 过滤无效日期
        df = df.dropna(subset=['原始日期', '月份']).copy()

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

        # 新增日期范围选择器（放在ITEM类型选择之后）
        use_custom_dates = st.sidebar.checkbox("📅 按日期自定义查询", help="启用后将忽略上方的分析范围选择")
        # 获取数据集中的日期范围
        min_date = df['原始日期'].min().to_pydatetime()
        max_date = df['原始日期'].max().to_pydatetime()
        # 设置默认日期范围（最近7天）
        default_end = max_date
        default_start = max_date - pd.DateOffset(days=6)
        # 日期选择器（仅在勾选时显示）
        if use_custom_dates:
            selected_dates = st.sidebar.date_input(
                "选择查询日期范围",
                value=(default_start, default_end),
                min_value=min_date,
                max_value=max_date,
                format="YYYY/MM/DD"  # 添加中文格式显示
            )
        else:
            selected_dates = (min_date, max_date)  # 默认使用全部日期范围

        # === 数据过滤和聚合 ===
        filtered = df[df.iloc[:, 4] == selected_item]
        # 动态日期列选择
        date_col = '原始日期' if use_custom_dates else '月份'
        # 增强日期范围过滤
        if use_custom_dates:
            # 使用B列原始日期过滤
            start_date = pd.to_datetime(selected_dates[0]).floor('D')
            end_date = pd.to_datetime(selected_dates[1]).ceil('D')
            filtered = filtered[
                (filtered['原始日期'] >= start_date) &
                (filtered['原始日期'] <= end_date)
                ]
            # 添加日期格式化列
            filtered['格式化日期'] = filtered['原始日期'].dt.strftime('%Y-%m-%d')
             # 添加平均值映射
            avg_values = filtered.groupby('原始日期')[comp].mean().reset_index()
            avg_mapping = avg_values.set_index('原始日期')[comp].to_dict()
            filtered['当日平均值'] = filtered['原始日期'].map(avg_mapping)
            
        else:
            # 使用C列月份过滤
            if selected_year != 'all':
                filtered = filtered[filtered['年份'] == selected_year]

        if not use_custom_dates:  # 原逻辑（聚合模式）
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
        else:  # 新增自定义日期模式（原始数据模式）
            # 直接使用原始数据，不进行聚合
            grouped = filtered.copy()
            grouped['date'] = grouped[date_col]

            # 时间轴配置（根据实际日期范围动态调整）
            date_diff = (end_date - start_date).days
            if date_diff <= 7:  # 周粒度
                tickformat = "%m-%d"
                dtick = "D1"
            elif date_diff <= 31:  # 月粒度
                tickformat = "%m-%d"
                dtick = "D3"
            else:  # 年粒度
                tickformat = "%Y-%m"
                dtick = "M1"

            x_col = 'date'  # 统一使用实际日期字段

        # === 可视化调整 ===
        st.title(f"{selected_item}质量趋势分析" + (f" - {selected_year}年" if selected_year != 'all' else ""))

        cols = chain(*[st.columns(2) for _ in range(4)])

        for idx, comp in enumerate(df.columns[5:12]):
            if idx >= 7:
                break

            with next(cols):
                if use_custom_dates:  # 自定义日期模式使用原始数据点   
                    # 计算每个日期的平均值
                    avg_values = filtered.groupby('原始日期')[comp].mean().reset_index()
                    avg_values['平均值'] = avg_values[comp].round(2)
                    avg_mapping = avg_values.set_index('原始日期')['平均值'].to_dict()          
                     # 将平均值映射到原始数据
                    filtered['当日平均值'] = filtered['原始日期'].map(avg_mapping)   
                    fig = px.scatter(  # 改用散点图显示每个数据点
                        plot_data,
                        x='原始日期',
                        y=comp,
                        title=None,
                        height=300,
                        template="plotly_dark",
                        opacity=0.7,
                        color_discrete_sequence=['#00ff9d'],
                        hover_data={
                            '格式化日期': True,  # 显示格式化日期
                            '当日平均值': ':.2f',
                            comp: False  # 保留两位小数
                        }
                    )
                    # 优化时间轴显示
                    fig.update_layout(
                        xaxis=dict(
                            tickformat="%m/%d",  # 显示月/日格式
                            tickvals=grouped['原始日期'],  # 显示所有日期刻度
                            tickangle=45 if len(grouped) > 10 else 0  # 数据点多时倾斜显示
                        )
                    )

                else:  # 原聚合模式
                    fig = px.line(
                        grouped,
                        x=x_col,
                        y=comp,
                        title=None,
                        markers=True,
                        height=300,
                        template="plotly_dark",
                    )

                # 统一颜色方案
                line_color = '#00ff9d'  # 荧光绿提高对比度
                grid_color = 'rgba(200, 200, 200, 0.2)'

                fig.update_layout(
                    margin=dict(l=20, r=20, t=80, b=60),
                    title={
                        'text': comp,  # 成分名称
                        'y': 0.95,  # 纵向位置（0-1区间）
                        'x': 0.5,  # 横向居中
                        'xanchor': 'center',
                        'yanchor': 'top',
                        'font': {
                            'size': 16,
                            'color': 'white'  # 与主题一致
                        }
                    },
                    xaxis=dict(
                        title=None,
                        tickformat=tickformat,
                        dtick=dtick,
                        tickangle=0,  # 统一设置为0度旋转
                        showgrid=False,
                        color='white'
                    ),
                    yaxis=dict(
                        title=None,
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
                        '<b>%{customdata[1]:.2f}</b>'  # 显示平均值
                        '<br>%{customdata[0]}'          # 显示日期
                        '<extra></extra>'
                    )
                )

                st.plotly_chart(fig, use_container_width=True)


    except Exception as e:
        st.error(f"程序运行错误: {str(e)}")
        st.stop()


if __name__ == "__main__":
    main()
