"""Decision maker entity type class of inseeds_farmer_management"""

# This file is part of pycopancore.
#
# Copyright (C) 2016-2017 by COPAN team at Potsdam Institute for Climate
# Impact Research
#
# URL: <http://www.pik-potsdam.de/copan/software>
# Contact: core@pik-potsdam.de
# License: BSD 2-clause license
import numpy as np
import pandas as pd

import inseeds.components.base as base


class DecisionMaker(base.Entity):
    """Decision Maker entity type class.
    
    This agent operates at the world level and has access to all cells
    in the world rather than being tied to individual cells. 
    #TODO: change this to world regions once we have them
    """

    # standard methods:
    def __init__(self, world=None, model=None, **kwargs):
        """Initialize an instance of DecisionMaker."""
        self.world = world
        self.model = model
        super().__init__(**kwargs)

        # Initialize basic attributes
        self.init_basic_attributes()

    def init_basic_attributes(self):
        """Initialize basic attributes for the decision maker."""
        
        # Basic identifier
        self.decision_maker_id = id(self)
        
        # Access to all cells in the world - defer if world is not available
        if hasattr(self, 'world') and self.world is not None:
            self.all_cells = self.world.cells
        else:
            self.all_cells = None
        
        # Belief value - represents the decision maker's belief about the system
        self.belief_value = 0  # Default neutral belief (-1.0 to 1.0)

    def init_world_attributes(self):
        """Initialize world-dependent attributes when world is available."""
        if hasattr(self, 'world') and self.world is not None:
            self.all_cells = self.world.cells

    @property
    def output_table(self):
        """Override output_table to handle world-level decision makers."""
        variables = self.get_defined_outputs()

        if not variables:
            return pd.DataFrame()
        else:
            df = super().output_table

            # For world-level decision makers, we don't have cell-specific data
            # So we use world-level identifiers instead
            df.insert(1, "cell", ["world"] * len(variables))
            df.insert(2, "lon", [0.0] * len(variables))  # No specific location
            df.insert(3, "lat", [0.0] * len(variables))   # No specific location

            # Add world-level attributes if available
            if hasattr(self, 'world') and self.world is not None:
                try:
                    if hasattr(self.world, "country"):
                        df.insert(4, "country", [str(self.world.country.item())] * len(variables))
                    if hasattr(self.world, "area"):
                        df.insert(
                            5,
                            "area [km2]",
                            [round(float(self.world.area.item()) * 1e-6, 4)] * len(variables),
                        )
                except (AttributeError, TypeError):
                    # If world attributes are not available, skip them
                    pass
            return df

    @property
    def decision_makers(self):
        """Return the set of all decision makers in the world."""
        if not hasattr(self, 'world') or self.world is None:
            return set()
        return {
            dm for dm in self.world.individuals 
            if dm.__class__.__name__ == "DecisionMaker"
        }

    @property
    def world_average_cropyield(self):
        """Return the average crop yield across all cells in the world."""
        if self.all_cells is None:
            return 1e-3
        all_yields = [
            cell.output.harvestc.values.mean() 
            for cell in self.world.cells 
            if cell.output.harvestc.values.mean() > 0
        ]
        if not all_yields:
            return 1e-3
        else:
            return np.mean(all_yields)

    @property
    def world_average_soilc(self):
        """Return the average soil carbon across all cells in the world."""
        if self.all_cells is None:
            return 1e-3
        all_soilc = [
            cell.output.soilc_agr_layer.values[0].item() 
            for cell in self.world.cells 
            if cell.output.soilc_agr_layer.values[0].item() > 0
        ]
        if not all_soilc:
            return 1e-3
        else:
            return np.mean(all_soilc)

    def update(self, t):
        """Update the decision maker."""
        # Basic update - can be extended later
        pass 