# Read the file
with open('live_paper_trading_system.py', 'r') as f:
    lines = f.readlines()

# Find the section and rewrite it correctly
output = []
i = 0
while i < len(lines):
    line = lines[i]
    if i == 286:  # Line 287 (0-indexed, so line 286 is line 287)
        # current_value line, keep it as is
        output.append(line)
        # Add the fixed code with correct indentation
        output.append('            # Handle string comparisons separately from numeric comparisons\n')
        output.append('            if isinstance(expected_value, str):\n')
        output.append('                if current_value != expected_value:\n')
        output.append('                    return False, f"{key}: expected {expected_value}, got {current_value}"\n')
        output.append('            else:\n')
        output.append('                if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance\n')
        output.append('                    return False, f"{key}: expected {expected_value}, got {current_value}"\n')
        # Skip the old broken lines
        while i < len(lines) and not (lines[i].strip() and not lines[i].startswith('            ') and 'return' in lines[i] and 'All parameters' in lines[i]):
            i += 1
        i -= 1  # Back up one since we'll increment at the end of the loop
    else:
        output.append(line)
    i += 1

# Write the fixed file
with open('live_paper_trading_system.py', 'w') as f:
    f.writelines(output)

print('File fixed with correct indentation!')
