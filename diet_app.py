"""
Diet Plan Viewer - Simple Streamlit App
Upload and view your daily diet plan from Excel, PDF, or Text files
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Optional imports - will be used if available
try:
    import openpyxl
except ImportError:
    pass

try:
    import pdfplumber
except ImportError:
    pass


def parse_excel(file):
    """Parse Excel file and extract diet plan data"""
    try:
        # Read Excel file
        df = pd.read_excel(file, engine='openpyxl')
        
        # Try to identify columns (flexible approach)
        df.columns = df.columns.str.lower().str.strip()
        
        # Look for common column names
        time_col = next((col for col in df.columns if 'time' in col), None)
        meal_col = next((col for col in df.columns if 'meal' in col), None)
        food_col = next((col for col in df.columns if 'food' in col or 'item' in col), None)
        qty_col = next((col for col in df.columns if 'quantity' in col or 'portion' in col or 'qty' in col), None)
        notes_col = next((col for col in df.columns if 'note' in col), None)
        
        # Create standardized dataframe
        meals = []
        for idx, row in df.iterrows():
            meal = {
                'time': row[time_col] if time_col else '',
                'meal': row[meal_col] if meal_col else '',
                'food': row[food_col] if food_col else '',
                'quantity': row[qty_col] if qty_col else '',
                'notes': row[notes_col] if notes_col else ''
            }
            # Skip empty rows
            if any(str(v).strip() and str(v) != 'nan' for v in meal.values()):
                meals.append(meal)
        
        return pd.DataFrame(meals)
    
    except Exception as e:
        st.error(f"Error parsing Excel file: {str(e)}")
        return None


def parse_pdf(file):
    """Parse PDF file and extract diet plan data"""
    try:
        import pdfplumber
        
        meals = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                
                # Split by lines and look for time patterns
                lines = text.split('\n')
                current_meal = {}
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for time pattern (e.g., "7:00 AM", "12:30 PM")
                    time_match = re.search(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\b', line)
                    
                    if time_match:
                        # Save previous meal if exists
                        if current_meal:
                            meals.append(current_meal)
                        
                        # Start new meal
                        current_meal = {
                            'time': time_match.group(1),
                            'meal': '',
                            'food': '',
                            'quantity': '',
                            'notes': ''
                        }
                        
                        # Extract meal name (text before time or after)
                        remaining = line.replace(time_match.group(1), '').strip()
                        meal_names = ['breakfast', 'lunch', 'dinner', 'snack']
                        for name in meal_names:
                            if name in remaining.lower():
                                current_meal['meal'] = name.title()
                                remaining = remaining.lower().replace(name, '').strip()
                                break
                        
                        if remaining:
                            current_meal['food'] = remaining
                    
                    elif current_meal:
                        # Add to current meal's food items
                        if current_meal['food']:
                            current_meal['food'] += ' | ' + line
                        else:
                            current_meal['food'] = line
                
                # Don't forget the last meal
                if current_meal:
                    meals.append(current_meal)
        
        return pd.DataFrame(meals) if meals else None
    
    except ImportError:
        st.error("PDF parsing library not available. Please install pdfplumber.")
        return None
    except Exception as e:
        st.error(f"Error parsing PDF file: {str(e)}")
        return None


def parse_text(file):
    """Parse text file and extract diet plan data"""
    try:
        # Read text file
        content = file.read().decode('utf-8')
        lines = content.split('\n')
        
        meals = []
        current_meal = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for time pattern
            time_match = re.search(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\b', line)
            
            if time_match:
                # Save previous meal
                if current_meal:
                    meals.append(current_meal)
                
                # Start new meal
                current_meal = {
                    'time': time_match.group(1),
                    'meal': '',
                    'food': '',
                    'quantity': '',
                    'notes': ''
                }
                
                # Extract meal info
                remaining = line.replace(time_match.group(1), '').strip()
                
                # Look for meal name
                meal_names = ['breakfast', 'lunch', 'dinner', 'snack', 'pre-workout', 'post-workout']
                for name in meal_names:
                    if name in remaining.lower():
                        current_meal['meal'] = name.title()
                        remaining = remaining.lower().replace(name, '').strip()
                        break
                
                # Rest is food
                if remaining:
                    current_meal['food'] = remaining
            
            elif current_meal:
                # Add to current meal
                if current_meal['food']:
                    current_meal['food'] += ' | ' + line
                else:
                    current_meal['food'] = line
        
        # Don't forget the last meal
        if current_meal:
            meals.append(current_meal)
        
        return pd.DataFrame(meals) if meals else None
    
    except Exception as e:
        st.error(f"Error parsing text file: {str(e)}")
        return None


def convert_time_to_datetime(time_str):
    """Convert time string to datetime for sorting"""
    try:
        # Handle various time formats
        time_str = str(time_str).strip()
        
        # Try parsing with AM/PM
        for fmt in ['%I:%M %p', '%I:%M%p', '%H:%M']:
            try:
                return datetime.strptime(time_str, fmt).time()
            except:
                continue
        
        return None
    except:
        return None


def get_current_or_next_meal(df):
    """Determine current or next meal based on current time"""
    now = datetime.now().time()
    
    # Convert time column to datetime.time objects
    df['time_obj'] = df['time'].apply(convert_time_to_datetime)
    df = df.dropna(subset=['time_obj'])
    
    if df.empty:
        return None
    
    # Sort by time
    df = df.sort_values('time_obj')
    
    # Find next meal
    for idx, row in df.iterrows():
        if row['time_obj'] > now:
            return idx
    
    # If no future meals, return first meal of tomorrow
    return df.index[0]


def main():
    st.set_page_config(
        page_title="Diet Plan Viewer",
        page_icon="🍽️",
        layout="wide"
    )
    
    st.title("🍽️ Diet Plan Viewer")
    st.markdown("Upload your diet plan and view your daily meals")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload your diet plan",
        type=['xlsx', 'pdf', 'txt'],
        help="Supported formats: Excel (.xlsx), PDF (.pdf), Text (.txt)"
    )
    
    if uploaded_file is not None:
        # Parse file based on type
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        with st.spinner(f"Parsing {file_extension.upper()} file..."):
            if file_extension == 'xlsx':
                df = parse_excel(uploaded_file)
            elif file_extension == 'pdf':
                df = parse_pdf(uploaded_file)
            elif file_extension == 'txt':
                df = parse_text(uploaded_file)
            else:
                st.error("Unsupported file type")
                return
        
        if df is not None and not df.empty:
            st.success(f"✅ Successfully loaded {len(df)} meals")
            
            # Display current time and next meal
            st.markdown("---")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.metric("Current Time", datetime.now().strftime("%I:%M %p"))
            
            with col2:
                next_meal_idx = get_current_or_next_meal(df)
                if next_meal_idx is not None:
                    next_meal = df.loc[next_meal_idx]
                    st.info(f"⏰ **Next Meal:** {next_meal['meal']} at {next_meal['time']}")
            
            st.markdown("---")
            
            # Display options
            view_mode = st.radio(
                "View Mode",
                ["Timeline View", "Table View"],
                horizontal=True
            )
            
            if view_mode == "Timeline View":
                # Timeline view - sorted by time
                st.subheader("📅 Daily Meal Schedule")
                
                # Try to sort by time
                df_sorted = df.copy()
                df_sorted['time_obj'] = df_sorted['time'].apply(convert_time_to_datetime)
                df_sorted = df_sorted.sort_values('time_obj', na_position='last')
                
                for idx, row in df_sorted.iterrows():
                    # Highlight current/next meal
                    if idx == next_meal_idx:
                        st.markdown(f"### 🔔 {row['time']} - {row['meal']}")
                    else:
                        st.markdown(f"### {row['time']} - {row['meal']}")
                    
                    if row['food']:
                        st.write(f"**Food Items:** {row['food']}")
                    if row['quantity']:
                        st.write(f"**Quantity:** {row['quantity']}")
                    if row['notes']:
                        st.write(f"**Notes:** {row['notes']}")
                    
                    st.markdown("---")
            
            else:
                # Table view
                st.subheader("📊 Meal Plan Table")
                
                # Prepare display dataframe
                display_df = df[['time', 'meal', 'food', 'quantity', 'notes']].copy()
                display_df.columns = ['Time', 'Meal', 'Food Items', 'Quantity', 'Notes']
                
                # Highlight next meal
                if next_meal_idx is not None:
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
        
        else:
            st.error("❌ Could not extract meal data from the file. Please check the file format.")
            st.info("""
            **Expected Format:**
            - Excel: Columns should include Time, Meal, Food/Items, Quantity
            - PDF/Text: Lines with time patterns (e.g., "7:00 AM - Breakfast")
            """)
    
    else:
        # Show instructions
        st.info("""
        ### 📝 How to use:
        1. Upload your diet plan file (Excel, PDF, or Text)
        2. The app will extract and display your meal schedule
        3. View your meals in Timeline or Table format
        4. Current/next meal will be highlighted
        
        ### 📋 File Format Guidelines:
        - **Excel**: Include columns for Time, Meal, Food Items, Quantity
        - **PDF/Text**: Format meals with time (e.g., "7:00 AM - Breakfast")
        - Times should be in 12-hour format (e.g., 7:00 AM, 12:30 PM)
        """)
        
        # Show example format
        with st.expander("📖 See Example Format"):
            example_data = {
                'Time': ['7:00 AM', '10:00 AM', '1:00 PM', '4:00 PM', '7:00 PM'],
                'Meal': ['Breakfast', 'Snack', 'Lunch', 'Snack', 'Dinner'],
                'Food Items': [
                    'Oatmeal with berries, Eggs',
                    'Greek yogurt, Almonds',
                    'Grilled chicken, Brown rice, Vegetables',
                    'Protein shake, Banana',
                    'Salmon, Sweet potato, Salad'
                ],
                'Quantity': ['1 bowl, 2 eggs', '1 cup, 10 pieces', '150g, 1 cup, 2 cups', '1 scoop, 1 medium', '150g, 1 medium, 2 cups'],
                'Notes': ['', '', '', '', '']
            }
            st.table(pd.DataFrame(example_data))


if __name__ == "__main__":
    main()
