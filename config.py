import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key-for-panhome-app')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///panhome.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    
    # NEW: User Roles
    USER_ROLES = [
        'Admin', 
        'Manager', 
        'Coordinator', 
        'Camp Boss', 
        'User'
    ]
    
    # NEW: Global Feature Permission Codes
    FEATURE_PERMISSIONS = {
        'INV_VIEW': 'View Inventory Dashboard & History',
        'INV_EDIT': 'Record Incoming/Outgoing Stock',
        'MAINT_EDIT': 'Add/Edit Maintenance Reports',
        'AMCS_EDIT': 'Add/Edit AMCs Services' 
    }
    
    # EXTENDED THEME OPTIONS (with descriptive names)
    THEME_OPTIONS = {
        'light': 'Default (Light Mode / Red Accent)',
        'dark': 'Dark Mode (Blue Accent)',
        'blue': 'Corporate Blue',
        'ocean': 'Ocean Blue',
        'skyblue': 'Sky Blue',
        'darkgreen': 'Dark Green',
        'darkgold': 'Dark Gold',
        'classic': 'Classic Dark Sidebar'
    }
    
    # EXTENDED FONT OPTIONS
    FONT_STYLES = {
        'inter': 'Inter (Default)',
        'poppins': 'Poppins',
        'roboto-slab': 'Roboto Slab',
        'open-sans': 'Open Sans',
        'merriweather': 'Merriweather (Serif)'
    }

    # EXTENDED FONT SIZE OPTIONS
    FONT_SIZES = {
        'small': 'Small (14px)',
        'normal': 'Normal (16px)',
        'large': 'Large (18px)',
        'xlarge': 'Extra Large (20px)'
    }
    
    # Static Data
    NATIONALITIES = ['Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda',
    'Argentina', 'Armenia', 'Aruba', 'Australia', 'Austria', 'Azerbaijan',
    'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium',
    'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana',
    'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Côte d\'Ivoire',
    'Cabo Verde', 'Cambodia', 'Cameroon', 'Canada', 'Central African Republic',
    'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 'Congo (Republic of)',
    'Congo (Democratic Republic of)', 'Costa Rica', 'Croatia', 'Cuba', 'Cyprus',
    'Czech Republic', 'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic',
    'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia',
    'Eswatini', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia',
    'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea',
    'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hungary', 'Iceland', 'India',
    'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Italy', 'Jamaica',
    'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'Kuwait', 'Kyrgyzstan',
    'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein',
    'Lithuania', 'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives',
    'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico',
    'Micronesia', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Morocco',
    'Mozambique', 'Myanmar', 'Namibia', 'Nauru', 'Nepal', 'Netherlands',
    'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'North Korea', 'North Macedonia',
    'Norway', 'Oman', 'Pakistan', 'Palau', 'Panama', 'Papua New Guinea', 'Paraguay',
    'Peru', 'Philippines', 'Poland', 'Portugal', 'Qatar', 'Romania', 'Russia',
    'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines',
    'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia', 'Senegal',
    'Serbia', 'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia',
    'Solomon Islands', 'Somalia', 'South Africa', 'South Korea', 'South Sudan',
    'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Sweden', 'Switzerland', 'Syria',
    'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 'Timor-Leste', 'Togo', 'Tonga',
    'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'Tuvalu', 'Uganda',
    'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States of America',
    'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam',
    'Yemen', 'Zambia', 'Zimbabwe'
]
    FOOD_VARIETIES = ['Non-Veg Rice', 'Veg Rice', 'Non-Veg Chapati', 'Veg Chapati', 'Arabic', 'Veg/Non-Veg Roti']
    MEAL_TIMES = ['Lunch', 'Dinner']
    EMPLOYEE_STATUSES = ['Active', 'Vacation', 'Resigned', 'Terminated', 'Other', 'On Leave', 'Check-in']