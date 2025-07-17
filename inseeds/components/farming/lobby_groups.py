"""Lobby group entity type class of inseeds_farmer_management"""

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


class LobbyGroup(core.Group):
    """Lobby Group (Group) entity type mixin class.
    
    This group operates at the world level and organizes farmers by their AFT.
    """

    # standard methods:
    def __init__(self, world=None, model=None, aft_type=None, **kwargs):
        """Initialize an instance of LobbyGroup."""
        # Pass world to the Group parent class (culture is optional now)
        super().__init__(world=world, **kwargs)  # must be the first line
        
        # Store model reference
        self.model = model
        
        # Store the AFT type this lobby group represents
        self.aft_type = aft_type

        # Initialize basic attributes
        self.init_basic_attributes()

    def init_basic_attributes(self):
        """Initialize basic attributes for the lobby group."""
        
        # Basic identifier
        self.lobby_group_id = id(self)
        
        # Access to all cells in the world - defer if world is not available
        if hasattr(self, 'world') and self.world is not None:
            self.all_cells = self.world.cells
        else:
            self.all_cells = None
        
        # Belief value - represents the lobby group's belief about the system
        self.belief_value = 0  # Default neutral belief (-1.0 to 1.0)
        
        # List to store farmers of this AFT type
        self.farmers = []

        # Agreement attribute (fraction of majority practice)
        self.agreement = 1.0  # Default to full agreement if no farmers

    def init_world_attributes(self):
        """Initialize world-dependent attributes when world is available."""
        if hasattr(self, 'world') and self.world is not None:
            self.all_cells = self.world.cells

    def add_farmer(self, farmer):
        """Add a farmer to this lobby group if they match the AFT type."""
        if farmer.aft == self.aft_type:
            self.farmers.append(farmer)
            return True
        return False

    def remove_farmer(self, farmer):
        """Remove a farmer from this lobby group."""
        if farmer in self.farmers:
            self.farmers.remove(farmer)
            return True
        return False

    def get_farmers(self):
        """Get all farmers in this lobby group."""
        return self.farmers

    def get_farmer_count(self):
        """Get the number of farmers in this lobby group."""
        return len(self.farmers)

    def update_farmers(self):
        """Update the farmer list by checking all farmers in the world."""
        if not hasattr(self, 'world') or self.world is None:
            return
            
        # Clear current farmers list
        self.farmers = []
        
        # Add farmers that match this AFT type
        for farmer in self.world.farmers:
            if farmer.aft == self.aft_type:
                self.farmers.append(farmer)

    def update(self, t):
        """Update the lobby group."""
        # Update farmer list
        self.update_farmers()
        
        # Update agreement based on farmers' practices
        if not self.farmers:
            self.agreement = 1.0  # No farmers, full agreement by default
        else:
            # Assume each farmer has a 'tillage' attribute (0 or 1)
            practices = [getattr(farmer, 'tillage', None) for farmer in self.farmers]
            # Filter out None values (in case some farmers don't have the attribute)
            practices = [p for p in practices if p is not None]
            if not practices:
                self.agreement = 1.0
            else:
                # Count the majority practice
                count_0 = practices.count(0)
                count_1 = practices.count(1)
                majority = max(count_0, count_1)
                self.agreement = majority / len(practices)
        # Basic update - can be extended later
        pass 