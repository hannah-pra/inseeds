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

import pycopancore.model_components.base as core
import inseeds.components.base as base


class DecisionMaker(core.Individual, base.Individual):
    """Decision Maker (Individual) entity type mixin class.
    
    This agent operates at the world level and has access to all cells
    in the world rather than being tied to individual cells. 
    #TODO: change this to world regions once we have them
    """

    # standard methods:
    def __init__(self, **kwargs):
        """Initialize an instance of DecisionMaker."""
        super().__init__(**kwargs)  # must be the first line

        # Initialize basic attributes
        self.init_basic_attributes()

    def init_basic_attributes(self):
        """Initialize basic attributes for the decision maker."""
        
        # Basic identifier
        self.decision_maker_id = id(self)
        
        # Access to all cells in the world
        self.all_cells = self.world.cells
        
        # Belief value - represents the decision maker's belief about the system
        self.belief_value = 0  # Default neutral belief (-1.0 to 1.0)

    @property
    def decision_makers(self):
        """Return the set of all decision makers in the world."""
        return {
            dm for dm in self.world.individuals 
            if dm.__class__.__name__ == "DecisionMaker"
        }

    @property
    def world_average_cropyield(self):
        """Return the average crop yield across all cells in the world."""
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
        super().update(t)
        
        # Basic update - can be extended later
        pass 