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
import pandas as pd

import pycopancore.model_components.base as core
from pycopancore.data_model.variable import Variable
import inseeds.components.base as base


class LobbyGroup(core.Group):
    """Lobby Group (Group) entity type mixin class.
    
    This group operates at the world level and organizes farmers by their AFT.
    """

    output_variables = base.Output(
        count_0=Variable(
            "count practice 0",
            "number of farmers with practice 0 (conservation tillage)",
        ),
        count_1=Variable(
            "count practice 1", 
            "number of farmers with practice 1 (conventional tillage)",
        ),
        majority=Variable(
            "majority practice count",
            "count of farmers with the majority practice",
        ),
        agreement=Variable(
            "agreement fraction",
            "fraction of farmers following the majority practice",
        ),
        contributed_yield=Variable(
            "contributed crop yield",
            "total crop yield contributed by all farmers in this lobby group (10% each)",
        ),
        farmer_count=Variable(
            "Farmer Count",
            "number of farmers in this lobby group",
        ),
    )

    # standard methods:
    def __init__(self, world=None, model=None, aft_type=None, **kwargs):
        """Initialize an instance of LobbyGroup."""
        # Pass world and culture to the Group parent class (culture is required as keyword)
        super().__init__(world=world, culture=None, **kwargs)  # must be the first line
        
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
        
        # Initialize count variables
        self.count_0 = 0
        self.count_1 = 0
        self.majority = 0
        
        # Initialize contributed yield
        self.contributed_yield = 0.0
        
        # Initialize farmer count
        self.farmer_count = 0

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

    def update_farmers(self):
        """Update the farmer list by checking all farmers in the world."""
        if not hasattr(self, 'world') or self.world is None:
            return
            
        # Clear current farmers list
        self.farmers = []
        
        # Add farmers that match this AFT type
        for farmer in self.world.farmers:
            if farmer.aft.value == self.aft_type.value:
                self.farmers.append(farmer)
        
    @property
    def output_table(self):
        """Override output_table to handle world-level lobby groups."""
        variables = self.get_defined_outputs()

        if not variables:
            return pd.DataFrame()
        else:
            # Create the base DataFrame with the standard structure
            df = pd.DataFrame(
                {
                    "year": [self.model.lpjml.sim_year] * len(variables),
                    "entity": [self.__class__.__name__] * len(variables),
                    "variable": [
                        getattr(
                            getattr(
                                self.__class__.output_variables, var, None
                            ),
                            "name",
                            None,
                        )
                        for var in variables
                    ],
                    "value": [getattr(self, var, None) for var in variables],
                    "unit": [
                        getattr(
                            getattr(
                                getattr(
                                    self.__class__.output_variables, var, None
                                ),
                                "unit",
                                None,
                            ),
                            "symbol",
                            None,
                        )
                        for var in variables
                    ],
                }
            )

            # For world-level lobby groups, we don't have cell-specific data
            # So we use world-level identifiers instead
            df.insert(1, "cell", ["world"] * len(variables))
            df.insert(2, "lon", [0.0] * len(variables))  # No specific location
            df.insert(3, "lat", [0.0] * len(variables))   # No specific location

            # Add world-level attributes if available
            if hasattr(self, 'world') and self.world is not None:
                try:
                    if hasattr(self.world, "country"):
                        # Handle xarray with multiple values - take the first non-zero value
                        country_data = self.world.country.values
                        if country_data.size > 0:
                            # Find first non-zero value
                            non_zero_indices = np.nonzero(country_data)[0]
                            if len(non_zero_indices) > 0:
                                country_value = country_data[non_zero_indices[0]]
                            else:
                                country_value = country_data[0] if country_data.size > 0 else 0
                        else:
                            country_value = 0
                        df.insert(4, "country", [str(country_value)] * len(variables))
                    if hasattr(self.world, "area"):
                        # Handle xarray with multiple values - take the first non-zero value
                        area_data = self.world.area.values
                        if area_data.size > 0:
                            # Find first non-zero value
                            non_zero_indices = np.nonzero(area_data)[0]
                            if len(non_zero_indices) > 0:
                                area_value = area_data[non_zero_indices[0]]
                            else:
                                area_value = area_data[0] if area_data.size > 0 else 0
                        else:
                            area_value = 0
                        df.insert(
                            5,
                            "area [km2]",
                            [round(float(area_value) * 1e-6, 4)] * len(variables),
                        )
                except (AttributeError, TypeError):
                    # If world attributes are not available, skip them
                    pass
            return df

    def get_defined_outputs(self):
        """Get the list of defined output variables for this entity."""
        # This method is inherited from base.Entity but needs to be overridden
        # because the model attribute points to the Component, not the Model
        if not hasattr(self, 'model') or self.model is None:
            return []
        
        # Try to access config through the model (Component)
        if hasattr(self.model, 'config'):
            config = self.model.config
        else:
            return []
            
        # Check if the output variables are defined for this entity type
        entity_name = self.__class__.__name__.lower()
        if hasattr(config, 'coupled_config') and hasattr(config.coupled_config, 'output'):
            output_dict = config.coupled_config.output.to_dict()
            if entity_name in output_dict:
                return [
                    var
                    for var in self.__class__.output_variables.names
                    if var in output_dict[entity_name]
                ]
        
        return []

    def update(self, t):
        """Update the lobby group."""
        # Update farmer list
        self.update_farmers()
        
        # Set farmer count
        self.farmer_count = len(self.farmers)
        
        # Update agreement based on farmers' practices
        if not self.farmers:
            self.agreement = 1.0  # No farmers, full agreement by default
            self.count_0 = 0
            self.count_1 = 0
            self.majority = 0
        else:
            # Assume each farmer has a 'tillage' attribute (0 or 1)
            practices = [getattr(farmer, 'tillage', None) for farmer in self.farmers]
            # Filter out None values (in case some farmers don't have the attribute)
            practices = [p for p in practices if p is not None]
            if not practices:
                self.agreement = 1.0
                self.count_0 = 0
                self.count_1 = 0
                self.majority = 0
            else:
                # Count the majority practice
                self.count_0 = practices.count(0)
                self.count_1 = practices.count(1)
                self.majority = max(self.count_0, self.count_1)
                self.agreement = self.majority / len(practices)
        
        # Calculate contributed yield from all farmers (10% each)
        self.contributed_yield = 0.0
        for farmer in self.farmers:
            if hasattr(farmer, 'lobby_contribution'):
                # Each farmer contributes 10% of their crop yield
                self.contributed_yield += farmer.lobby_contribution