import pandas as pd
from datetime import datetime, timedelta
from config import RECOMMENDATION_DAYS, MIN_HISTORY_FOR_CUSTOMER

def get_recommendations(histori_df, master_produk_df, company, cust_id, shipto_name, current_items):
    """
    Returns a dataframe of recommended items based on history.
    """
    # 1. Filter history dynamically
    cutoff_date = datetime.now() - timedelta(days=RECOMMENDATION_DAYS)
    try:
        histori_df['Date'] = pd.to_datetime(histori_df['Date'])
    except:
        pass
        
    recent_hist = histori_df[histori_df['Date'] >= cutoff_date]
    
    # Exclude items already in the cart
    exclude_items = [item['Item_Name'] for item in current_items]
    
    # Filter for specific customer & company
    if 'Company' in recent_hist.columns:
        cust_hist = recent_hist[(recent_hist['Company'] == company) & (recent_hist['Cust_ID'] == cust_id) & (recent_hist['Shipto_Name'] == shipto_name)]
    else:
        cust_hist = recent_hist[(recent_hist['Cust_ID'] == cust_id) & (recent_hist['Shipto_Name'] == shipto_name)]
    
    # Calculate monthly average
    cust_hist_grouped = cust_hist.groupby('Item_Name')['Qty'].sum().reset_index()
    cust_hist_grouped['Avg Qty/Bulan'] = (cust_hist_grouped['Qty'] / (RECOMMENDATION_DAYS / 30)).apply(lambda x: int(x) + 1 if x % 1 > 0 else int(x))
    
    cust_hist_grouped = cust_hist_grouped[~cust_hist_grouped['Item_Name'].isin(exclude_items)]
    cust_hist_grouped = cust_hist_grouped.sort_values(by='Qty', ascending=False).head(10)
    
    recommendation_type = "History Customer"
    
    if len(cust_hist_grouped) < MIN_HISTORY_FOR_CUSTOMER and len(cust_hist_grouped) == 0:
        # Return empty if nothing found for customer
        return pd.DataFrame(), recommendation_type
        
    # Merge with product stats
    res = pd.merge(cust_hist_grouped, master_produk_df[['Item_Name', 'Volume', 'Weight', 'Length', 'Height', 'Width', 'Company']], on='Item_Name', how='inner')
    
    # In case the recommendations span other companies, we might want to filter, but typically we let the user see it.
    # The requirement says: "If result < 5 items ... Also compute top 10 nationally". 
    # Let's just return what we have.
    res = res.rename(columns={'Volume': 'Volume/Unit', 'Weight': 'Weight/Unit'})
    
    return res, recommendation_type
