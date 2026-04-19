# Read the file
with open('live_paper_trading_system.py', 'r') as f:
    lines = f.readlines()

# Find and modify the specific lines
output = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this is the problematic line
    if 'if abs(current_value - expected_value) > 1e-9:' in line:
        # Replace with new logic
        output.append('             # Handle string comparisons separately from numeric comparisons\n')
        output.append('             if isinstance(expected_value, str):\n')
        output.append('                 if current_value != expected_value:\n')
        output.append('                     return False, f"{key}: expected {expected_value}, got {current_value}"\n')
        output.append('             else:\n')
        output.append('                 if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance\n')
        i += 1
        # Get the next line (the return False)
        output.append(lines[i])
    else:
        output.append(line)
    i += 1

# Write the fixed file
with open('live_paper_trading_system.py', 'w') as f:
    f.writelines(output)

print('File fixed successfully with line-by-line replacement!')
