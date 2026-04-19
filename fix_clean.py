# Read the file
with open('live_paper_trading_system.py', 'r') as f:
    content = f.read()

# Replace the entire broken section with correct code
old_section = '''            current_value = current_params.get(key)
             # Handle string comparisons separately from numeric comparisons
            # Handle string comparisons separately from numeric comparisons
            if isinstance(expected_value, str):
                if current_value != expected_value:
                    return False, f"{key}: expected {expected_value}, got {current_value}"
            else:
                if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance
                    return False, f"{key}: expected {expected_value}, got {current_value}"
        return True, "All parameters locked and verified"'''

new_section = '''            current_value = current_params.get(key)
            # Handle string comparisons separately from numeric comparisons
            if isinstance(expected_value, str):
                if current_value != expected_value:
                    return False, f"{key}: expected {expected_value}, got {current_value}"
            else:
                if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance
                    return False, f"{key}: expected {expected_value}, got {current_value}"

        return True, "All parameters locked and verified"'''

new_content = content.replace(old_section, new_section)

# Write the fixed file
with open('live_paper_trading_system.py', 'w') as f:
    f.write(new_content)

print('File cleaned up successfully!')
