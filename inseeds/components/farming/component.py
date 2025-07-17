from inseeds.components import base


class Component(base.Component):
    """Model mixing class for farmer_management.
    This component initializes farmers in the model to make decisions
    on which management practices to apply to their fields.
    Two practices are available: conventional and conservation tillage.
    The theory of planned behaviour is used to model farmer decision-making.
    Two farmer AFTs are implemented, the traditionalist and the pioneer.
    """

    def init_farmers(self, farmer_class, **kwargs):
        """Initialize farmers."""
        farmers = []

        for cell in self.world.cells:
            if cell.output.cftfrac.sum("band") == 0:
                continue

            farmer = farmer_class(cell=cell, model=self)
            farmers.append(farmer)

        farmers_sorted = sorted(farmers, key=lambda farmer: farmer.avg_hdate)
        for farmer in farmers_sorted:
            farmer.init_neighbourhood()

        # self.world.farmers = set(farmers_sorted

    def init_decision_makers(self, decision_maker_class, **kwargs):
        """Initialize decision makers."""
        decision_makers = []

        # Create a few decision makers at the world level (not tied to cells)
        num_decision_makers = getattr(
            self.model.config.coupled_config, 'num_decision_makers', 3
        )
        
        for i in range(num_decision_makers):
            decision_maker = decision_maker_class(world=self.world, model=self)
            decision_makers.append(decision_maker)

    def init_lobby_groups(self, lobby_group_class, **kwargs):
        """Initialize lobby groups."""
        lobby_groups = []

        # Create a few lobby groups at the world level
        num_lobby_groups = getattr(
            self.model.config.coupled_config, 'num_lobby_groups', 2
        )
        
        for i in range(num_lobby_groups):
            lobby_group = lobby_group_class(world=self.world, model=self)
            lobby_group.init_world_attributes()  # Initialize world-dependent attributes
            lobby_groups.append(lobby_group)

    def update(self, t):
        super().update(t)

        # Update farmers
        farmers_sorted = sorted(
            self.world.farmers, key=lambda farmer: farmer.avg_hdate
        )
        for farmer in farmers_sorted:
            farmer.update(t)

        # Update decision makers
        decision_makers_sorted = sorted(
            self.world.decision_makers, 
            key=lambda dm: dm.decision_maker_id
        )
        for decision_maker in decision_makers_sorted:
            decision_maker.update(t)

        # Update lobby groups
        lobby_groups_sorted = sorted(
            self.world.lobby_groups, 
            key=lambda lg: lg.lobby_group_id
        )
        for lobby_group in lobby_groups_sorted:
            lobby_group.update(t)
