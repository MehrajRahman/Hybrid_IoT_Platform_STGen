#!/bin/bash
# MQTT Protocol Plugin Installation Script for STGen

set -e

echo "=================================================="
echo "  STGen MQTT Protocol Plugin Installer"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python
echo -e "${YELLOW}[1/4] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED} Python 3 not found. Please install Python 3.7+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN} Python $PYTHON_VERSION found${NC}"
echo ""

# Install Python dependencies
echo -e "${YELLOW}[2/4] Installing Python dependencies...${NC}"
pip install paho-mqtt==1.6.1
echo -e "${GREEN} paho-mqtt installed${NC}"
echo ""

# Check for MQTT broker
echo -e "${YELLOW}[3/4] Checking for MQTT broker...${NC}"
if command -v mosquitto &> /dev/null; then
    echo -e "${GREEN} Mosquitto broker found${NC}"
    MOSQUITTO_VERSION=$(mosquitto -h 2>&1 | grep "mosquitto version" | cut -d' ' -f3)
    echo "   Version: $MOSQUITTO_VERSION"
else
    echo -e "${YELLOW}  Mosquitto broker not found${NC}"
    echo ""
    echo "Would you like to install Mosquitto broker? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "Installing Mosquitto on Linux..."
            sudo apt-get update
            sudo apt-get install -y mosquitto mosquitto-clients
            sudo systemctl start mosquitto
            sudo systemctl enable mosquitto
            echo -e "${GREEN} Mosquitto installed and started${NC}"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "Installing Mosquitto on macOS..."
            if ! command -v brew &> /dev/null; then
                echo -e "${RED} Homebrew not found. Install from https://brew.sh${NC}"
                exit 1
            fi
            brew install mosquitto
            brew services start mosquitto
            echo -e "${GREEN} Mosquitto installed and started${NC}"
        else
            echo -e "${YELLOW}  Automatic installation not supported on this OS${NC}"
            echo "Please install Mosquitto manually:"
            echo "  - Ubuntu/Debian: sudo apt-get install mosquitto"
            echo "  - macOS: brew install mosquitto"
            echo "  - Windows: https://mosquitto.org/download/"
            echo "  - Docker: docker run -d -p 1883:1883 eclipse-mosquitto"
        fi
    else
        echo -e "${YELLOW}  Skipping broker installation${NC}"
        echo "You can use a public test broker or install later"
    fi
fi
echo ""

# Verify installation
echo -e "${YELLOW}[4/4] Verifying installation...${NC}"

# Test Python import
if python3 -c "import paho.mqtt.client" 2>/dev/null; then
    echo -e "${GREEN} Python MQTT client working${NC}"
else
    echo -e "${RED} Python MQTT client import failed${NC}"
    exit 1
fi

# Test broker connection (if running)
if command -v mosquitto &> /dev/null && pgrep -x mosquitto > /dev/null; then
    echo "Testing broker connection..."
    timeout 2 mosquitto_sub -h 127.0.0.1 -t "test" -C 1 &> /dev/null && \
        echo -e "${GREEN} Broker connection working${NC}" || \
        echo -e "${YELLOW}  Broker connection test failed (may be normal)${NC}"
fi
echo ""

# Summary
echo "=================================================="
echo -e "${GREEN}  Installation Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Ensure MQTT broker is running:"
echo "     sudo systemctl status mosquitto"
echo ""
echo "  2. Run MQTT test:"
echo "     python -m stgen.main configs/mqtt.json"
echo ""
echo "  3. Monitor broker (optional):"
echo "     mosquitto_sub -h 127.0.0.1 -t 'stgen/#' -v"
echo ""
echo "For troubleshooting, see protocols/mqtt/README.md"
echo ""