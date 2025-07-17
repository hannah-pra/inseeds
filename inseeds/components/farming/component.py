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

        # Import AFT enum from farmer module
        from inseeds.components.farming.farmer import AFT

        # Create two lobby groups - one for each AFT type
        traditionalist_group = lobby_group_class(
            world=self.world, 
            model=self, 
            aft_type=AFT.traditionalist
        )
        traditionalist_group.init_world_attributes()
        lobby_groups.append(traditionalist_group)

        pioneer_group = lobby_group_class(
            world=self.world, 
            model=self, 
            aft_type=AFT.pioneer
        )
        pioneer_group.init_world_attributes()
        lobby_groups.append(pioneer_group)

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
