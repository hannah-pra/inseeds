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
            "total crop yield contributed by all farmers in this lobby group (5% each)",
        ),
        usable_budget=Variable(
            "usable budget",
            "effective lobbying budget: agreement × contributed yield",
        ),
        lobby_attempts=Variable(
            "lobby attempts",
            "number of lobby attempts made this year",
        ),
        successful_lobby_attempts=Variable(
            "successful lobby attempts",
            "number of successful lobby attempts this year",
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
        
        # Initialize lobbying-related attributes
        self.lobby_strategy = 0  # Default to traditionalist strategy
        self.lobby_cost_per_attempt = 1.0  # Default cost
        self.decision_maker_relationships = {}  # Track relationships with DMs
        self.lobby_attempts = {}  # Track attempts per DM
        self.successful_lobby_attempts = {}  # Track successes per DM
        self.consecutive_failures = 0  # Track consecutive failures
        
        # Set lobby strategy and cost from configuration if available
        self._configure_lobbying()
        self.count_0 = 0
        self.count_1 = 0
        self.majority = 0
        
        # Initialize contributed yield
        self.contributed_yield = 0.0
        
        # Initialize usable budget
        self.usable_budget = 0.0
        
        # Initialize farmer count
        self.farmer_count = 0

    def init_world_attributes(self):
        """Initialize world-dependent attributes when world is available."""
        if hasattr(self, 'world') and self.world is not None:
            self.all_cells = self.world.cells
            
        # Initialize relationship tracking with decision makers
        self.decision_maker_relationships = {}  # {decision_maker_id: relationship_value}

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
                    "value": [self.get_output_value(var) for var in variables],
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
        
        # Calculate contributed yield from all farmers (5% each)
        self.contributed_yield = 0.0
        for farmer in self.farmers:
            if hasattr(farmer, 'lobby_contribution'):
                # Each farmer contributes 5% of their crop yield
                self.contributed_yield += farmer.lobby_contribution
        
        # Calculate usable budget: agreement × contributed yield
        self.usable_budget = self.agreement * self.contributed_yield
        
        # Update belief value based on agreement and practice preferences
        self.update_belief_value()
    
    def update_belief_value(self):
        """Update the lobby group's belief value based on agreement and practice preferences.
        
        Belief value ranges from -1.0 to 1.0:
        - -1.0: All farmers agree on conventional practices (tillage = 1)
        - 0.0: Half/half split or no clear majority
        - 1.0: All farmers agree on conservation practices (tillage = 0)
        
        The belief value is weighted by the agreement level:
        - High agreement = stronger belief (closer to -1 or 1)
        - Low agreement = weaker belief (closer to 0)
        """
        if not self.farmers:
            # No farmers - neutral belief
            self.belief_value = 0.0
            return
        
        # Calculate the proportion of conservation farmers (practice 0)
        total_farmers = len(self.farmers)
        conservation_farmers = self.count_0
        conventional_farmers = self.count_1
        
        if total_farmers == 0:
            self.belief_value = 0.0
            return
        
        # Calculate the proportion of conservation vs conventional
        conservation_proportion = conservation_farmers / total_farmers
        conventional_proportion = conventional_farmers / total_farmers
        
        # Calculate base belief value:
        # -1.0 if all conventional, +1.0 if all conservation
        base_belief = (conservation_proportion - conventional_proportion)
        
        # Weight by agreement level to get final belief value
        # High agreement = stronger belief, low agreement = weaker belief
        self.belief_value = base_belief * self.agreement
        
        # Ensure belief value stays within [-1.0, 1.0] range
        self.belief_value = max(-1.0, min(1.0, self.belief_value))
    
    def get_total_lobby_attempts(self):
        """Get total lobby attempts across all decision makers."""
        return sum(self.lobby_attempts.values()) if self.lobby_attempts else 0
    
    def get_total_successful_attempts(self):
        """Get total successful lobby attempts across all decision makers."""
        return sum(self.successful_lobby_attempts.values()) if self.successful_lobby_attempts else 0
    
    def get_output_value(self, var_name):
        """Get the appropriate output value for a variable, handling special cases."""
        if var_name == 'lobby_attempts':
            return self.get_total_lobby_attempts()
        elif var_name == 'successful_lobby_attempts':
            return self.get_total_successful_attempts()
        else:
            return getattr(self, var_name, None)
    
    def get_target_decision_makers(self, decision_makers):
        """Get list of decision makers to target based on lobby strategy.
        
        Strategy 0: Target similar beliefs (highest success probability)
        Strategy 1: Target swing voters (beliefs around 0)
        Strategy 2: Target opposite beliefs (high risk, high gain)
        """
        if not decision_makers:
            return []
        
        # Convert to list if it's a set
        dm_list = list(decision_makers)
        
        if self.lobby_strategy == 0:
            # Target similar beliefs - sort by belief difference (ascending)
            dm_list.sort(key=lambda dm: abs(dm.belief_value - self.belief_value))
        elif self.lobby_strategy == 1:
            # Target swing voters - sort by absolute belief value (ascending)
            dm_list.sort(key=lambda dm: abs(dm.belief_value))
        elif self.lobby_strategy == 2:
            # Target opposite beliefs - sort by belief difference (descending)
            dm_list.sort(key=lambda dm: abs(dm.belief_value - self.belief_value), reverse=True)
        
        return dm_list
    
    def attempt_lobby(self, decision_maker):
        """Attempt to lobby a decision maker.
        
        Returns True if successful, False otherwise.
        """
        # Get or initialize relationship value
        if decision_maker.decision_maker_id not in self.decision_maker_relationships:
            self.decision_maker_relationships[decision_maker.decision_maker_id] = 0.5
        
        relationship_value = self.decision_maker_relationships[decision_maker.decision_maker_id]
        
        # Calculate belief difference
        belief_difference = abs(self.belief_value - decision_maker.belief_value)
        
        # Calculate success probability
        success_probability = relationship_value * (1.0 / (1.0 + belief_difference))
        
        # Determine success
        import random
        success = random.random() < success_probability
        
        # Update relationship value
        if success:
            # Successful attempt increases relationship
            self.decision_maker_relationships[decision_maker.decision_maker_id] = min(
                1.0, 
                relationship_value + 0.05
            )
        else:
            # Failed attempt doesn't change relationship immediately
            pass
        
        return success
    
    def conduct_lobbying_campaign(self, decision_makers):
        """Conduct lobbying campaign against available decision makers."""
        if not decision_makers or self.usable_budget <= 0:
            # No budget or decision makers - update relationships for all DMs
            self._update_all_relationships(decision_makers)
            return
        
        # Calculate number of lobby attempts based on budget
        max_attempts = int(self.usable_budget / self.lobby_cost_per_attempt)
        
        if max_attempts <= 0:
            # No attempts possible - update relationships for all DMs
            self._update_all_relationships(decision_makers)
            return
        
        # Get target decision makers based on strategy
        target_dms = self.get_target_decision_makers(decision_makers)
        
        # Reset counters for this year
        self.lobby_attempts = {}
        self.successful_lobby_attempts = {}
        
        # Initialize counters for each decision maker
        for dm in decision_makers:
            self.lobby_attempts[dm.decision_maker_id] = 0
            self.successful_lobby_attempts[dm.decision_maker_id] = 0
        
        # Make lobby attempts
        for i, decision_maker in enumerate(target_dms):
            if i >= max_attempts:
                break
                
            self.lobby_attempts[decision_maker.decision_maker_id] += 1
            
            if self.attempt_lobby(decision_maker):
                self.successful_lobby_attempts[decision_maker.decision_maker_id] += 1
        
        # Apply strategic adjustments based on campaign results
        self._apply_strategic_adjustments()
        
        # Update relationships after lobbying campaign
        self._update_all_relationships(decision_makers)
    
    def _update_all_relationships(self, decision_makers):
        """Update relationship values for all decision makers after lobbying campaign."""
        for dm in decision_makers:
            dm_id = dm.decision_maker_id
            
            # Initialize relationship if it doesn't exist
            if dm_id not in self.decision_maker_relationships:
                self.decision_maker_relationships[dm_id] = 0.5
            
            # Check if this decision maker was lobbied this year
            was_lobbied = self.lobby_attempts.get(dm_id, 0) > 0
            
            if was_lobbied:
                # Relationship was already updated during lobbying attempts
                # No additional change needed
                pass
            else:
                # No lobbying this year - decrease relationship slightly
                current_relationship = self.decision_maker_relationships[dm_id]
                self.decision_maker_relationships[dm_id] = max(
                    0.0, 
                    current_relationship - 0.02  # Smaller decrease for no lobbying
                )
    
    def _apply_strategic_adjustments(self):
        """Apply strategic adjustments based on lobbying campaign results."""
        total_attempts = sum(self.lobby_attempts.values())
        total_successes = sum(self.successful_lobby_attempts.values())
        
        if total_attempts == 0:
            return
        
        success_rate = total_successes / total_attempts
        
        # Adjust strategy based on success rate
        if success_rate < 0.2:  # Very low success
            # Consider changing strategy if consistently failing
            if hasattr(self, 'consecutive_failures'):
                self.consecutive_failures += 1
            else:
                self.consecutive_failures = 1
            
            if self.consecutive_failures >= 3:
                # Switch to more conservative strategy
                if self.lobby_strategy == 2:  # Pioneer strategy
                    self.lobby_strategy = 1  # Switch to swing voters
                elif self.lobby_strategy == 1:  # Swing voters
                    self.lobby_strategy = 0  # Switch to similar beliefs
                self.consecutive_failures = 0
        else:
            # Reset failure counter on success
            if hasattr(self, 'consecutive_failures'):
                self.consecutive_failures = 0
    
    def get_lobbying_statistics(self):
        """Get comprehensive lobbying statistics for this lobby group."""
        total_attempts = sum(self.lobby_attempts.values())
        total_successes = sum(self.successful_lobby_attempts.values())
        
        stats = {
            'total_attempts': total_attempts,
            'total_successes': total_successes,
            'success_rate': total_successes / total_attempts if total_attempts > 0 else 0.0,
            'strategy': self.lobby_strategy,
            'strategy_name': self._get_strategy_name(),
            'usable_budget': self.usable_budget,
            'contributed_yield': self.contributed_yield,
            'agreement': self.agreement,
            'belief_value': self.belief_value,
            'consecutive_failures': getattr(self, 'consecutive_failures', 0)
        }
        
        return stats
    
    def _get_strategy_name(self):
        """Get human-readable name for the current lobbying strategy."""
        strategy_names = {
            0: "Traditionalist (Target Similar Beliefs)",
            1: "Swing Voter (Target Neutral Beliefs)", 
            2: "Pioneer (Target Opposite Beliefs)"
        }
        return strategy_names.get(self.lobby_strategy, "Unknown")
    
    def _configure_lobbying(self):
        """Configure lobbying strategy and cost from model configuration."""
        if hasattr(self, 'model') and self.model is not None:
            if hasattr(self.model, 'config') and self.model.config is not None:
                if hasattr(self.model.config, 'coupled_config') and self.model.config.coupled_config is not None:
                    coupled_config = self.model.config.coupled_config
                    
                    # Set lobby strategy based on AFT type
                    if hasattr(coupled_config, 'lobby_groups') and coupled_config.lobby_groups is not None:
                        lobby_config = coupled_config.lobby_groups
                        
                        if self.aft_type.value == 'AFT.traditionalist':
                            self.lobby_strategy = getattr(lobby_config, 'traditionalist_strategy', 0)
                        elif self.aft_type.value == 'AFT.pioneer':
                            self.lobby_strategy = getattr(lobby_config, 'pioneer_strategy', 2)
                        
                        # Set lobby cost per attempt
                        self.lobby_cost_per_attempt = getattr(lobby_config, 'lobby_cost_per_attempt', 1.0)
    
    def update_relationships(self):
        """Legacy method - now handled within conduct_lobbying_campaign."""
        # This method is kept for backward compatibility but is no longer used
        pass