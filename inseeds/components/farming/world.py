"""The inseeds_farmer_mnagement.world class."""

import inseeds.components.base as base
from pycopancore.data_model.variable import Variable


class World(base.World):
    """World entity type mixin class."""
    
    output_variables = base.Output(
        shared_subsidy_budget=Variable(
            "Shared Subsidy Budget",
            "total shared budget available for subsidies (40% of world average crop yield)"
        )
    )

    def __init__(self, **kwargs):
        """Initialize an instance of World."""
        super().__init__(**kwargs)
        
        # Initialize networks for social interactions
        self.init_networks()
    
    def init_networks(self):
        """Initialize acquaintance and group membership networks."""
        try:
            import networkx as nx
            
            # Create acquaintance network
            self.acquaintance_network = nx.Graph()
            
            # Create group membership network
            self.group_membership_network = nx.Graph()
            
            print("DEBUG: Networks initialized successfully")
            print(f"DEBUG: acquaintance_network type: {type(self.acquaintance_network)}")
            print(f"DEBUG: group_membership_network type: {type(self.group_membership_network)}")
            
        except ImportError:
            print("DEBUG: networkx not available, networks will not be initialized")
            self.acquaintance_network = None
            self.group_membership_network = None



    @property
    def farmers(self):
        """Return the set of all farmers."""
        farmers = {
            farmer
            for farmer in self.individuals
            if farmer.__class__.__name__ == "Farmer"  # noqa
        }
        return farmers

    @property
    def decision_makers(self):
        """Return the set of all decision makers."""
        decision_makers = {
            decision_maker
            for decision_maker in self.individuals
            if decision_maker.__class__.__name__ == "DecisionMaker"  # noqa
        }
        return decision_makers

    @property
    def lobby_groups(self):
        """Return the set of all lobby groups."""
        lobby_groups = {
            lobby_group
            for lobby_group in self.groups
            if lobby_group.__class__.__name__ == "LobbyGroup"  # noqa
        }
        return lobby_groups

    @property
    def shared_subsidy_budget(self):
        """Return the current shared subsidy budget."""
        return getattr(self, '_shared_subsidy_budget', 0.0)
    
    @shared_subsidy_budget.setter
    def shared_subsidy_budget(self, value):
        """Set the shared subsidy budget."""
        self._shared_subsidy_budget = value
    
    def get_defined_outputs(self):
        """Get the list of defined output variables for this entity."""
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
                result = [
                    var
                    for var in self.__class__.output_variables.names
                    if var in output_dict[entity_name]
                ]
                return result
        
        return []
    
    