import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import itertools
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression, RFE
import joblib
import os
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    print('='*50)
    print('CRISP-DM Phase 1: Business Understanding')
    print('='*50)
    print('Objective: Predict the Profit of startups based on their spending and location.')

    print('='*50)
    print('CRISP-DM Phase 2: Data Understanding (EDA)')
    print('='*50)
    # Use absolute path based on the script location to avoid FileNotFoundError
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, '50_Startups.csv')
    if not os.path.exists(file_path):
        print('Error: '+file_path+' not found.')
        return

    dataset = pd.read_csv(file_path)
    
    print('--- 1. Basic Information ---')
    print(dataset.info())
    print('Missing Values:')
    print(dataset.isnull().sum())
    
    print('--- 2. Descriptive Statistics ---')
    print(dataset.describe())
    
    print('--- 3. Correlation Matrix ---')
    numeric_dataset = dataset.select_dtypes(include=['float64', 'int64'])
    corr_matrix = numeric_dataset.corr()
    print(corr_matrix)
    
    print('Generating EDA Plots...')
    sns.set_theme(style='whitegrid')
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('EDA for 50 Startups Dataset', fontsize=16)

    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', ax=axes[0, 0])
    axes[0, 0].set_title('Correlation Heatmap')

    sns.scatterplot(x='R&D Spend', y='Profit', data=dataset, hue='State', ax=axes[0, 1])
    axes[0, 1].set_title('R&D Spend vs Profit')

    sns.boxplot(x='State', y='Profit', data=dataset, ax=axes[1, 0])
    axes[1, 0].set_title('Profit Distribution by State')

    sns.histplot(dataset['Profit'], kde=True, ax=axes[1, 1], color='green')
    axes[1, 1].set_title('Distribution of Profit')

    plt.tight_layout()
    eda_plot_path = os.path.join(script_dir, 'eda_plots.png')
    plt.savefig(eda_plot_path)
    print(f'EDA Plots saved to {eda_plot_path}')

    print('='*50)
    print('CRISP-DM Phase 3: Data Preparation')
    print('='*50)
    X = dataset.iloc[:, :-1].values
    y = dataset.iloc[:, -1].values

    ct = ColumnTransformer(transformers=[('encoder', OneHotEncoder(drop='first'), [3])], remainder='passthrough')
    X = ct.fit_transform(X)
    
    print('Categorical feature State encoded using OneHotEncoder.')

    print('--- Transformed Features (First 5 Rows) ---')
    print('| is_Florida | is_New_York | R&D Spend | Administration | Marketing Spend |')
    print('|:---:|:---:|:---|:---|:---|')
    for row in X[:5]:
        print('| '+str(row[0])+' | '+str(row[1])+' | '+str(round(row[2], 2))+' | '+str(round(row[3], 2))+' | '+str(round(row[4], 2))+' |')
    print('')

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print('Data split into training set ('+str(len(X_train))+' samples) and test set ('+str(len(X_test))+' samples).')

    print('='*50)
    print('CRISP-DM Phase 4: Modeling')
    print('='*50)
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    print('Multiple Linear Regression model trained successfully.')

    print('='*50)
    print('CRISP-DM Phase 5: Evaluation')
    print('='*50)
    y_pred = regressor.predict(X_test)
    
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    
    print('R-squared Score: '+str(round(r2, 4)))
    print('Mean Absolute Error (MAE): '+str(round(mae, 2)))
    print('Mean Squared Error (MSE): '+str(round(mse, 2)))
    print('Root Mean Squared Error (RMSE): '+str(round(np.sqrt(mse), 2)))

    print('\n--- 5 Machine Learning Models on 16 Feature Combinations ---')
    dataset_encoded = pd.get_dummies(dataset, columns=['State'], dtype=int)
    combo_features = ['R&D Spend', 'Marketing Spend', 'State_California', 'State_Florida', 'State_New York']
    X_all_encoded = dataset_encoded[combo_features]
    y_target = dataset_encoded['Profit']
    
    # 定義 5 種要比較的機器學習模型
    ml_models = {
        'Linear Regression': LinearRegression(),
        'Lasso (L1)': Lasso(alpha=1000, random_state=42),
        'Ridge (L2)': Ridge(alpha=1.0, random_state=42),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
    }
    
    combo_metrics = []
    
    # 針對這 16 種組合，讓 5 個模型都跑過一次 (共 80 次測試)
    for k in range(1, len(combo_features) + 1):
        for combo in itertools.combinations(combo_features, k):
            if 'R&D Spend' not in combo:
                continue
            X_combo = X_all_encoded[list(combo)].values
            X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_combo, y_target, test_size=0.2, random_state=42)
            
            # 特徵標準化 (這對 Ridge、Lasso 演算法至關重要)
            scaler_c = StandardScaler()
            X_train_c_s = scaler_c.fit_transform(X_train_c)
            X_test_c_s = scaler_c.transform(X_test_c)
            
            for m_name, model in ml_models.items():
                model.fit(X_train_c_s, y_train_c)
                y_pred_c = model.predict(X_test_c_s)
                
                combo_metrics.append({
                    'Model': m_name,
                    'Num_Features': k,
                    'Features': ", ".join(combo),
                    'R-squared': r2_score(y_test_c, y_pred_c),
                    'RMSE': np.sqrt(mean_squared_error(y_test_c, y_pred_c))
                })
                
    combo_df = pd.DataFrame(combo_metrics)
    # 依照 R-squared 遞減排序
    combo_df_sorted = combo_df.sort_values(by='R-squared', ascending=False).reset_index(drop=True)
    
    print("Top 10 Model + Feature Combinations by R-squared:")
    print(combo_df_sorted.head(10).to_string(index=False))
    
    csv_path = os.path.join(script_dir, 'feature_combinations_5models_metrics.csv')
    combo_df_sorted.to_csv(csv_path, index=False)
    print(f"\nAll combination metrics saved to '{csv_path}'")

    sns.set_theme(style="whitegrid", rc={"axes.facecolor": "#f8f9fa", "grid.color": "#e9ecef"})
    
    # ==========================================
    # 產出 5 張圖：5 種機器學習模型個別的 16 種組合表現 (原始圖表格式)
    # ==========================================
    for m_name in ml_models.keys():
        model_df = combo_df[combo_df['Model'] == m_name].copy()
        
        best_per_k_m = model_df.loc[model_df.groupby('Num_Features')['R-squared'].idxmax()]
        best_rmse_per_k_m = model_df.loc[model_df.groupby('Num_Features')['RMSE'].idxmin()]
        
        fig_m = plt.figure(figsize=(14, 10), facecolor='white')
        fig_m.suptitle(f'{m_name} - Feature Combinations Predictive Performance', fontsize=20, fontweight='bold', color='#2c3e50', y=0.98)
        
        ax1_m = plt.subplot2grid((3, 2), (0, 0))
        ax2_m = plt.subplot2grid((3, 2), (0, 1))
        ax_table_m = plt.subplot2grid((3, 2), (1, 0), colspan=2, rowspan=2)
        
        # 折線圖 1: R-squared
        sns.lineplot(x='Num_Features', y='R-squared', data=best_per_k_m, marker='o', markersize=10, linewidth=2.5, ax=ax1_m, color='#0077b6')
        ax1_m.set_title('Highest R-squared vs Number of Features', fontsize=14, fontweight='bold', color='#343a40', pad=10)
        ax1_m.set_xticks(range(1, 6))
        ax1_m.set_xlabel('Number of Features', fontsize=12, fontweight='medium')
        ax1_m.set_ylabel('R-squared Score', fontsize=12, fontweight='medium')
        
        # 折線圖 2: RMSE
        sns.lineplot(x='Num_Features', y='RMSE', data=best_rmse_per_k_m, marker='s', markersize=10, linewidth=2.5, ax=ax2_m, color='#d90429')
        ax2_m.set_title('Lowest RMSE vs Number of Features', fontsize=14, fontweight='bold', color='#343a40', pad=10)
        ax2_m.set_xticks(range(1, 6))
        ax2_m.set_xlabel('Number of Features', fontsize=12, fontweight='medium')
        ax2_m.set_ylabel('RMSE', fontsize=12, fontweight='medium')
        
        # 表格 (16 種組合)
        ax_table_m.axis('off')
        ax_table_m.set_title(f'16 Feature Combinations for {m_name}', fontsize=15, fontweight='bold', color='#2c3e50', pad=15)
        
        table_df_m = model_df.sort_values(by=['Num_Features', 'R-squared'], ascending=[True, False]).reset_index(drop=True)
        table_df_m['RMSE'] = table_df_m['RMSE'].apply(lambda x: f"{x:.2f}")
        table_df_m['R-squared'] = table_df_m['R-squared'].apply(lambda x: f"{x:.4f}")
        
        table_data_m = table_df_m[['Num_Features', 'Features', 'R-squared', 'RMSE']].values.tolist()
        col_labels_m = ['Num_Features', 'Features', 'R-squared', 'RMSE']
        
        tbl_m = ax_table_m.table(cellText=table_data_m, colLabels=col_labels_m, loc='center', cellLoc='center', colWidths=[0.1, 0.6, 0.15, 0.15])
        tbl_m.auto_set_font_size(False)
        tbl_m.set_fontsize(11)
        tbl_m.scale(1, 1.8)
        
        for (row, col), cell in tbl_m.get_celld().items():
            cell.set_edgecolor('#dee2e6')
            if row == 0:
                cell.set_text_props(weight='bold', color='white', fontsize=12)
                cell.set_facecolor('#495057')
            else:
                cell.set_facecolor('#f8f9fa' if row % 2 == 0 else 'white')
                if col == 1:
                    cell.set_text_props(ha='left')
                    cell.get_text().set_text('  ' + cell.get_text().get_text())

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        safe_m_name = m_name.replace(' ', '_').replace('(', '').replace(')', '')
        plot_path_m = os.path.join(script_dir, f'feature_combinations_{safe_m_name}.png')
        plt.savefig(plot_path_m, bbox_inches='tight', dpi=300)
        plt.close(fig_m)
        print(f"Saved individual model plot: {plot_path_m}")

    # ==========================================
    # 產出第 6 張圖：匯總 5 種方法前 10 好的結果 (原始圖表格式)
    # ==========================================
    best_per_k_all = combo_df.loc[combo_df.groupby(['Model', 'Num_Features'])['R-squared'].idxmax()].reset_index(drop=True)
    best_rmse_per_k_all = combo_df.loc[combo_df.groupby(['Model', 'Num_Features'])['RMSE'].idxmin()].reset_index(drop=True)
    
    fig_all = plt.figure(figsize=(16, 11), facecolor='white')
    fig_all.suptitle('5 ML Models Performance Across 16 Feature Combinations', fontsize=20, fontweight='bold', color='#2c3e50', y=0.98)
    
    ax1_all = plt.subplot2grid((3, 2), (0, 0))
    ax2_all = plt.subplot2grid((3, 2), (0, 1))
    ax_table_all = plt.subplot2grid((3, 2), (1, 0), colspan=2, rowspan=2)
    
    sns.lineplot(x='Num_Features', y='R-squared', hue='Model', data=best_per_k_all, marker='o', markersize=9, linewidth=2.5, ax=ax1_all, palette='tab10')
    ax1_all.set_title('Highest R-squared vs Number of Features', fontsize=14, fontweight='bold', color='#343a40', pad=10)
    ax1_all.set_xticks(range(1, 6))
    
    sns.lineplot(x='Num_Features', y='RMSE', hue='Model', data=best_rmse_per_k_all, marker='s', markersize=9, linewidth=2.5, ax=ax2_all, palette='tab10')
    ax2_all.set_title('Lowest RMSE vs Number of Features', fontsize=14, fontweight='bold', color='#343a40', pad=10)
    ax2_all.set_xticks(range(1, 6))
    
    ax_table_all.axis('off')
    ax_table_all.set_title('Overall Top 10 Best Model & Feature Combinations', fontsize=15, fontweight='bold', color='#2c3e50', pad=15)
    
    top10_df = combo_df_sorted.head(10).copy()
    top10_df['RMSE'] = top10_df['RMSE'].apply(lambda x: f"{x:.2f}")
    top10_df['R-squared'] = top10_df['R-squared'].apply(lambda x: f"{x:.4f}")
    
    tbl_all = ax_table_all.table(cellText=top10_df.values.tolist(), colLabels=top10_df.columns.tolist(), loc='center', cellLoc='center', colWidths=[0.15, 0.1, 0.45, 0.15, 0.15])
    tbl_all.auto_set_font_size(False)
    tbl_all.set_fontsize(11)
    tbl_all.scale(1, 1.8)
    
    for (row, col), cell in tbl_all.get_celld().items():
        cell.set_edgecolor('#dee2e6')
        if row == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=12)
            cell.set_facecolor('#495057')
        else:
            cell.set_facecolor('#f8f9fa' if row % 2 == 0 else 'white')
            if col == 2: # Features column left aligned
                cell.set_text_props(ha='left')
                cell.get_text().set_text('  ' + cell.get_text().get_text())

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plot_path_all = os.path.join(script_dir, 'feature_combinations_top10_overall.png')
    plt.savefig(plot_path_all, bbox_inches='tight', dpi=300)
    plt.close(fig_all)
    print(f"Saved overall top 10 summary plot: {plot_path_all}")

    print('\n--- 5 Feature Selection Algorithms Comparison ---')
    dataset_fs = pd.get_dummies(dataset, columns=['State'], drop_first=True, dtype=int)
    fs_feature_names = [col for col in dataset_fs.columns if col != 'Profit']
    X_fs = dataset_fs[fs_feature_names]
    y_fs = dataset_fs['Profit']
    
    X_train_fs, X_test_fs, y_train_fs, y_test_fs = train_test_split(X_fs, y_fs, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_fs_scaled = pd.DataFrame(scaler.fit_transform(X_train_fs), columns=fs_feature_names)
    X_test_fs_scaled = pd.DataFrame(scaler.transform(X_test_fs), columns=fs_feature_names)

    fs_results = []
    
    # 針對 Embedded 方法預先訓練好，以取得重要性分數 / 係數
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train_fs_scaled, y_train_fs)
    rf_importances = pd.Series(rf.feature_importances_, index=fs_feature_names)

    lasso = Lasso(alpha=1000, random_state=42)
    lasso.fit(X_train_fs_scaled, y_train_fs)
    lasso_coefs = pd.Series(np.abs(lasso.coef_), index=fs_feature_names)

    def eval_fs_model(features):
        model = LinearRegression()
        model.fit(X_train_fs_scaled[features], y_train_fs)
        preds = model.predict(X_test_fs_scaled[features])
        return r2_score(y_test_fs, preds), np.sqrt(mean_squared_error(y_test_fs, preds))

    # 測試 1 到 5 個特徵數量 (Number of Features)
    for k in range(1, len(fs_feature_names) + 1):
        # 1. F-Test
        f_sel = SelectKBest(score_func=f_regression, k=k)
        f_sel.fit(X_train_fs_scaled, y_train_fs)
        f_feats = X_train_fs_scaled.columns[f_sel.get_support()].tolist()
        r2_f, rmse_f = eval_fs_model(f_feats)
        fs_results.append({'Algorithm': 'F-Test', 'Num_Features': k, 'Features': ", ".join(f_feats), 'R-squared': r2_f, 'RMSE': rmse_f})

        # 2. Mutual Info
        mi_sel = SelectKBest(score_func=mutual_info_regression, k=k)
        mi_sel.fit(X_train_fs_scaled, y_train_fs)
        mi_feats = X_train_fs_scaled.columns[mi_sel.get_support()].tolist()
        r2_mi, rmse_mi = eval_fs_model(mi_feats)
        fs_results.append({'Algorithm': 'Mutual Info', 'Num_Features': k, 'Features': ", ".join(mi_feats), 'R-squared': r2_mi, 'RMSE': rmse_mi})

        # 3. Random Forest
        rf_feats = rf_importances.nlargest(k).index.tolist()
        r2_rf, rmse_rf = eval_fs_model(rf_feats)
        fs_results.append({'Algorithm': 'Random Forest', 'Num_Features': k, 'Features': ", ".join(rf_feats), 'R-squared': r2_rf, 'RMSE': rmse_rf})

        # 4. RFE
        rfe_sel = RFE(LinearRegression(), n_features_to_select=k, step=1)
        rfe_sel.fit(X_train_fs_scaled, y_train_fs)
        rfe_feats = X_train_fs_scaled.columns[rfe_sel.get_support()].tolist()
        r2_rfe, rmse_rfe = eval_fs_model(rfe_feats)
        fs_results.append({'Algorithm': 'RFE', 'Num_Features': k, 'Features': ", ".join(rfe_feats), 'R-squared': r2_rfe, 'RMSE': rmse_rfe})

        # 5. Lasso
        lasso_feats = lasso_coefs.nlargest(k).index.tolist()
        r2_lasso, rmse_lasso = eval_fs_model(lasso_feats)
        fs_results.append({'Algorithm': 'Lasso (L1)', 'Num_Features': k, 'Features': ", ".join(lasso_feats), 'R-squared': r2_lasso, 'RMSE': rmse_lasso})

    fs_df = pd.DataFrame(fs_results)
    
    # Plotting (Matching feature_combinations_metrics style)
    fig_fs = plt.figure(figsize=(14, 10), facecolor='white')
    fig_fs.suptitle('Feature Selection Algorithms Predictive Performance', fontsize=20, fontweight='bold', color='#2c3e50', y=0.98)

    ax_line1 = plt.subplot2grid((3, 2), (0, 0))
    ax_line2 = plt.subplot2grid((3, 2), (0, 1))
    ax_table_fs = plt.subplot2grid((3, 2), (1, 0), colspan=2, rowspan=2)

    # X 軸為特徵數量的折線圖
    sns.lineplot(x='Num_Features', y='R-squared', hue='Algorithm', data=fs_df, marker='o', markersize=8, linewidth=2, ax=ax_line1)
    ax_line1.set_title('R-squared vs Number of Features', fontsize=14, fontweight='bold', pad=10)
    ax_line1.set_xticks(range(1, len(fs_feature_names) + 1))
    
    sns.lineplot(x='Num_Features', y='RMSE', hue='Algorithm', data=fs_df, marker='s', markersize=8, linewidth=2, ax=ax_line2)
    ax_line2.set_title('RMSE vs Number of Features', fontsize=14, fontweight='bold', pad=10)
    ax_line2.set_xticks(range(1, len(fs_feature_names) + 1))

    # Table subplot setup
    ax_table_fs.axis('off')
    target_k = 3
    ax_table_fs.set_title(f'Feature Selection Algorithms (Top {target_k} Features Selected)', fontsize=15, fontweight='bold', color='#2c3e50', pad=15)
    
    # 固定顯示挑選 3 個特徵的結果，方便與圖表 x=3 的點直接對照
    best_fs_df = fs_df[fs_df['Num_Features'] == target_k].copy()
    best_fs_df = best_fs_df.sort_values(by='R-squared', ascending=False).reset_index(drop=True)
    
    fs_table_df = best_fs_df[['Algorithm', 'Num_Features', 'Features', 'R-squared', 'RMSE']].copy()
    fs_table_df['RMSE'] = fs_table_df['RMSE'].apply(lambda x: f"{x:.2f}")
    fs_table_df['R-squared'] = fs_table_df['R-squared'].apply(lambda x: f"{x:.4f}")
    
    tbl_fs = ax_table_fs.table(cellText=fs_table_df.values.tolist(), colLabels=fs_table_df.columns.tolist(), loc='center', cellLoc='center', colWidths=[0.15, 0.12, 0.45, 0.14, 0.14])
    tbl_fs.auto_set_font_size(False)
    tbl_fs.set_fontsize(11)
    tbl_fs.scale(1, 1.8)
    
    for (row, col), cell in tbl_fs.get_celld().items():
        cell.set_edgecolor('#dee2e6')
        if row == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=12)
            cell.set_facecolor('#495057')
        else:
            cell.set_facecolor('#f8f9fa' if row % 2 == 0 else 'white')
            if col == 2:  # Features 欄位
                cell.set_text_props(ha='left')
                cell.get_text().set_text('  ' + cell.get_text().get_text())

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    fs_plot_path = os.path.join(script_dir, 'feature_selection_algorithms_metrics.png')
    plt.savefig(fs_plot_path, bbox_inches='tight', dpi=300)
    print(f'Feature selection algorithms metrics chart saved to {fs_plot_path}')

    print('='*50)
    print('CRISP-DM Phase 6: Deployment')
    print('='*50)
    model_filename = os.path.join(script_dir, 'multiple_linear_regression_model.joblib')
    preprocessor_filename = os.path.join(script_dir, 'preprocessor.joblib')
    
    joblib.dump(regressor, model_filename)
    joblib.dump(ct, preprocessor_filename)
    print('Model saved as '+model_filename)
    print('Preprocessor saved as '+preprocessor_filename)
    print('Deployment phase complete.')

if __name__ == '__main__':
    main()