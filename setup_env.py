"""
Environment setup helper for Millionaire 2026
Helps configure and verify API credentials and settings
"""

import os
from pathlib import Path


class EnvironmentSetup:
    """Environment configuration helper"""
    
    @staticmethod
    def get_env_path():
        """Get the .env file path"""
        return Path.home() / '.millionaire_2026_env'
    
    @staticmethod
    def setup_credentials():
        """Interactively setup API credentials"""
        print("\n" + "="*60)
        print("MILLIONAIRE 2026 - ENVIRONMENT SETUP")
        print("="*60)
        
        env_vars = {}
        
        # Coinbase API setup (optional for paper trading)
        print("\n1. COINBASE API SETUP (Optional for paper trading)")
        print("   Get credentials from: https://www.coinbase.com/settings/api")
        print("   Leave blank to skip")
        
        api_key = input("\n   Enter Coinbase API Key: ").strip()
        if api_key:
            api_secret = input("   Enter Coinbase API Secret: ").strip()
            if api_secret:
                env_vars['COINBASE_API_KEY'] = api_key
                env_vars['COINBASE_API_SECRET'] = api_secret
                print("   [OK] Coinbase credentials saved")
            else:
                print("   [ERROR] API Secret required if using API Key")
        else:
            print("   - Skipping Coinbase setup (will use mock trading)") 
        
        # MCF Server setup (optional)
        print("\n2. MCF SERVER SETUP (Optional)")
        print("   Default: http://localhost:8000")
        mcf_url = input("   Enter MCF Server URL (or press Enter for default): ").strip()
        if mcf_url:
            env_vars['MCF_SERVER_URL'] = mcf_url
        else:
            env_vars['MCF_SERVER_URL'] = 'http://localhost:8000'
        print(f"   [OK] MCF Server: {env_vars['MCF_SERVER_URL']}")
        
        # Trading settings
        print("\n3. TRADING SETTINGS")
        initial_capital = input("   Initial capital (default $10,000): ").strip()
        if initial_capital:
            try:
                env_vars['INITIAL_CAPITAL'] = str(float(initial_capital))
                print(f"   [OK] Initial capital: ${float(initial_capital):,.2f}")
            except ValueError:
                print("   [ERROR] Invalid amount")
                env_vars['INITIAL_CAPITAL'] = '10000'
        else:
            env_vars['INITIAL_CAPITAL'] = '10000'
            print("   [OK] Initial capital: $10,000 (default)")
        
        # Risk settings
        print("\n4. RISK SETTINGS")
        max_daily_loss = input("   Max daily loss % (default 5%): ").strip()
        if max_daily_loss:
            try:
                env_vars['MAX_DAILY_LOSS_PCT'] = str(float(max_daily_loss))
                print(f"   [OK] Max daily loss: {float(max_daily_loss)}%")
            except ValueError:
                print("   [ERROR] Invalid percentage")
                env_vars['MAX_DAILY_LOSS_PCT'] = '5.0'
        else:
            env_vars['MAX_DAILY_LOSS_PCT'] = '5.0'
            print("   [OK] Max daily loss: 5% (default)")
        
        return env_vars
    
    @staticmethod
    def save_env_vars(env_vars):
        """Save environment variables to file"""
        env_file = EnvironmentSetup.get_env_path()
        
        # Set in current session
        for key, value in env_vars.items():
            os.environ[key] = value
        
        print(f"\n[OK] Environment variables configured")
        print(f"  API credentials: {'Set' if 'COINBASE_API_KEY' in env_vars else 'Not set'}")
        print(f"  MCF Server: {env_vars.get('MCF_SERVER_URL', 'N/A')}")
        print(f"  Initial Capital: ${float(env_vars.get('INITIAL_CAPITAL', 10000)):,.2f}")
        print(f"  Max Daily Loss: {env_vars.get('MAX_DAILY_LOSS_PCT', 5.0)}%")
    
    @staticmethod
    def verify_setup():
        """Verify environment setup"""
        print("\n" + "="*60)
        print("ENVIRONMENT VERIFICATION")
        print("="*60)
        
        checks = {
            'COINBASE_API_KEY': 'Coinbase API Key',
            'COINBASE_API_SECRET': 'Coinbase API Secret',
            'MCF_SERVER_URL': 'MCF Server URL',
            'INITIAL_CAPITAL': 'Initial Capital',
            'MAX_DAILY_LOSS_PCT': 'Max Daily Loss %'
        }
        
        all_good = True
        for env_var, description in checks.items():
            value = os.environ.get(env_var)
            if value:
                if 'API' in env_var and len(value) > 10:
                    print(f"[OK] {description}: {'*' * 10}...{value[-4:]}")
                else:
                    print(f"[OK] {description}: {value}")
            else:
                if env_var in ['COINBASE_API_KEY', 'COINBASE_API_SECRET']:
                    print(f"[WARN] {description}: Not set (will use mock trading)")
                else:
                    print(f"[INFO] {description}: Not set")
                    all_good = False
        
        if all_good:
            print("\n[OK] Environment fully configured!")
        else:
            print("\n[WARN] Some optional settings not configured")
        
        return all_good


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        # Interactive setup
        env_vars = EnvironmentSetup.setup_credentials()
        EnvironmentSetup.save_env_vars(env_vars)
        EnvironmentSetup.verify_setup()
    else:
        # Just verify
        print("Running environment verification...")
        EnvironmentSetup.verify_setup()
        print("\nTo setup environment, run: python setup_env.py --setup")
