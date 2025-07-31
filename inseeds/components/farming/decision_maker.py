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
from pycopancore.data_model.variable import Variable


class DecisionMaker(base.Individual):
    """Decision Maker entity type."""
    
    output_variables = base.Output(
        decision_maker_id=Variable("Decision Maker ID", "unique identifier for decision maker"),
        belief_value=Variable("Belief Value", "decision maker's belief about the system (-1.0 to 1.0)"),
        world_average_cropyield=Variable("World Average Crop Yield", "average crop yield across all cells"),
        world_average_soilc=Variable("World Average Soil C", "average soil carbon across all cells"),
    )
    
    # standard methods:
    def __init__(self, world=None, model=None, **kwargs):
        """Initialize an instance of DecisionMaker."""
        self.world = world
        self.model = model
        super().__init__(model=model, **kwargs)

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

            # For world-level decision makers, we don't have cell-specific data
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

    def get_defined_outputs(self):
        """Get the list of defined output variables for this entity."""
        # This method is inherited from base.Entity but needs to be overridden
        # because the model attribute points to the Component, not the Model
        if not hasattr(self, 'model') or self.model is None:
            print(f"DEBUG: model is None or doesn't exist")
            return []
        
        # Try to access config through the model (Component)
        if hasattr(self.model, 'config'):
            config = self.model.config
        else:
            print(f"DEBUG: model has no config attribute")
            return []
            
        # Check if the output variables are defined for this entity type
        entity_name = self.__class__.__name__.lower()
        print(f"DEBUG: entity_name = {entity_name}")
        
        if hasattr(config, 'coupled_config') and hasattr(config.coupled_config, 'output'):
            output_dict = config.coupled_config.output.to_dict()
            print(f"DEBUG: output_dict keys = {list(output_dict.keys())}")
            if entity_name in output_dict:
                print(f"DEBUG: entity_name found in output_dict")
                print(f"DEBUG: output_dict[{entity_name}] = {output_dict[entity_name]}")
                print(f"DEBUG: self.__class__.output_variables.names = {self.__class__.output_variables.names}")
                result = [
                    var
                    for var in self.__class__.output_variables.names
                    if var in output_dict[entity_name]
                ]
                print(f"DEBUG: result = {result}")
                return result
            else:
                print(f"DEBUG: entity_name not found in output_dict")
        else:
            print(f"DEBUG: config has no coupled_config or output")
        
        return [] 