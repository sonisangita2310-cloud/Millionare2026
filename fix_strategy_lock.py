# Read the file
with open('live_paper_trading_system.py', 'r') as f:
    content = f.read()

# Find and replace the problematic lines
old_code = """        # Check if all parameters match
         for key, expected_value in expected_params.items():
             current_value = current_params.get(key)
             if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance
                 return False, f"{key}: expected {expected_value}, got {current_value}" """

new_code = """        # Check if all parameters match
         for key, expected_value in expected_params.items():
             current_value = current_params.get(key)
             # Handle string comparisons separately from numeric comparisons
             if isinstance(expected_value, str):
                 if current_value != expected_value:
                     return False, f"{key}: expected {expected_value}, got {current_value}"
             else:
                 if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance
                     return False, f"{key}: expected {expected_value}, got {current_value}" """

new_content = content.replace(old_code, new_code)

# Write the fixed file
with open('live_paper_trading_system.py', 'w') as f:
    f.write(new_content)

print('File fixed successfully!')
