# Decision Maker Agent

This document explains how to use the new `DecisionMaker` agent alongside the existing `Farmer` agent in the InSEEDS farming component.

## Overview

The `DecisionMaker` agent operates at the world level rather than being tied to individual cells like the `Farmer` agent. This allows for global access to all cells in the world.

## Key Differences from Farmer

| Aspect | Farmer | DecisionMaker |
|--------|--------|---------------|
| **Scope** | Cell-level | World-level |
| **Data Source** | Individual cell data | All cells in world |
| **Focus** | Local farming practices | Global access to all cells |
| **Network** | Neighboring farmers | All cells in world |

## Usage

### 1. Import the DecisionMaker

```python
from inseeds.components.farming import DecisionMaker
```

### 2. Initialize Decision Makers in Your Model

Add this to your model's `__init__` method:

```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    
    # Initialize farmers (existing code)
    self.init_farmers(farmer_class=Farmer)
    
    # Initialize decision makers (new)
    self.init_decision_makers(decision_maker_class=DecisionMaker)
```

### 3. Configuration

Add decision maker parameters to your config file:

```yaml
# Decision maker configuration
num_decision_makers: 3  # Number of decision makers to create
```

### 4. Accessing World Data

The decision maker has access to all cells in the world:

```python
# Access all cells
all_cells = decision_maker.all_cells

# Get world averages
avg_yield = decision_maker.world_average_cropyield
avg_soilc = decision_maker.world_average_soilc
```

### 5. Accessing Decision Makers

```python
# Get all decision makers
decision_makers = self.world.decision_makers

# Access individual decision maker
for dm in decision_makers:
    print(f"Decision Maker ID: {dm.decision_maker_id}")
    print(f"Number of cells: {len(dm.all_cells)}")
```

### 6. Basic Properties

Decision makers have these basic properties:

- `decision_maker_id`: Unique identifier
- `all_cells`: Access to all cells in the world
- `world_average_cropyield`: Average crop yield across all cells
- `world_average_soilc`: Average soil carbon across all cells

## Example Integration

Here's a complete example of how to integrate decision makers into your model:

```python
from inseeds.components.farming import Farmer, DecisionMaker
from inseeds.components.farming import Component

class MyComponent(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize both farmers and decision makers
        self.init_farmers(farmer_class=Farmer)
        self.init_decision_makers(decision_maker_class=DecisionMaker)
    
    def update(self, t):
        super().update(t)
        
        # The base update method will handle both farmers and decision makers
        # You can add additional logic here if needed
```

## Extending the Decision Maker

The decision maker is intentionally simple and can be extended as needed:

```python
class MyDecisionMaker(DecisionMaker):
    def update(self, t):
        super().update(t)
        
        # Add your custom logic here
        # You have access to self.all_cells for all world data
        pass
```

## World-Level Access

The decision maker provides a way to access and analyze data across all cells in the world, which can be useful for:

- Global statistics and monitoring
- World-level decision making
- Policy analysis
- System-wide interventions 