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

        # Debug: Check if world has networks
        print(f"DEBUG: World has acquaintance_network: {hasattr(self.world, 'acquaintance_network')}")
        print(f"DEBUG: World has group_membership_network: {hasattr(self.world, 'group_membership_network')}")
        if hasattr(self.world, 'acquaintance_network'):
            print(f"DEBUG: acquaintance_network type: {type(self.world.acquaintance_network)}")
        if hasattr(self.world, 'group_membership_network'):
            print(f"DEBUG: group_membership_network type: {type(self.world.group_membership_network)}")

        for cell in self.world.cells:
            if cell.output.cftfrac.sum("band") == 0:
                continue

            farmer = farmer_class(cell=cell, model=self)
            farmers.append(farmer)

        farmers_sorted = sorted(farmers, key=lambda farmer: farmer.avg_hdate)
        for farmer in farmers_sorted:
            farmer.init_neighbourhood()

        # Create acquaintance networks within AFT groups
        self.create_aft_acquaintance_networks(farmers_sorted)

    def create_aft_acquaintance_networks(self, farmers):
        """Create acquaintance networks within AFT groups."""
        if not hasattr(self.world, 'acquaintance_network'):
            print("DEBUG: No acquaintance network available")
            return
            
        # Group farmers by AFT
        traditionalist_farmers = [f for f in farmers if f.aft.name == 'traditionalist']
        pioneer_farmers = [f for f in farmers if f.aft.name == 'pioneer']
        
        print(f"DEBUG: Creating acquaintance networks - {len(traditionalist_farmers)} traditionalists, {len(pioneer_farmers)} pioneers")
        
        # Add all farmers to the network
        for farmer in farmers:
            self.world.acquaintance_network.add_node(farmer)
        
        # Create edges between traditionalist farmers
        for i, farmer1 in enumerate(traditionalist_farmers):
            for farmer2 in traditionalist_farmers[i+1:]:
                self.world.acquaintance_network.add_edge(farmer1, farmer2)
                print(f"DEBUG: Added edge between traditionalist farmers {farmer1.cell.grid.cell.item()} and {farmer2.cell.grid.cell.item()}")
        
        # Create edges between pioneer farmers
        for i, farmer1 in enumerate(pioneer_farmers):
            for farmer2 in pioneer_farmers[i+1:]:
                self.world.acquaintance_network.add_edge(farmer1, farmer2)
                print(f"DEBUG: Added edge between pioneer farmers {farmer1.cell.grid.cell.item()} and {farmer2.cell.grid.cell.item()}")
        
        print(f"DEBUG: Created {len(traditionalist_farmers) * (len(traditionalist_farmers) - 1) // 2} traditionalist edges")
        print(f"DEBUG: Created {len(pioneer_farmers) * (len(pioneer_farmers) - 1) // 2} pioneer edges")

    def init_decision_makers(self, decision_maker_class, **kwargs):
        """Initialize decision makers."""
        decision_makers = []

        # Create a few decision makers at the world level (not tied to cells)
        num_decision_makers = getattr(
            self.config.coupled_config, 'num_decision_makers', 3
        )
        
        print(f"Creating {num_decision_makers} decision makers...")
        
        for i in range(num_decision_makers):
            decision_maker = decision_maker_class(world=self.world, model=self)
            decision_makers.append(decision_maker)
            
        # Add decision makers to the world's individuals list
        for decision_maker in decision_makers:
            self.world.individuals.add(decision_maker)
            
        # Also store in world.decision_makers for the update method
        if not hasattr(self.world, 'decision_makers'):
            self.world.decision_makers = set()
        self.world.decision_makers.update(decision_makers)
            
        print(f"Added {len(decision_makers)} decision makers to world. Total individuals: {len(self.world.individuals)}")
        
        # Debug: check if decision makers are in the world
        dm_count = sum(1 for ind in self.world.individuals if ind.__class__.__name__ == "DecisionMaker")
        print(f"Debug: Found {dm_count} DecisionMaker instances in world.individuals")
        
        # Debug: check what types of individuals are in the world
        individual_types = {}
        for ind in self.world.individuals:
            class_name = ind.__class__.__name__
            individual_types[class_name] = individual_types.get(class_name, 0) + 1
        print(f"Debug: Individual types in world: {individual_types}")
        
        return decision_makers

    def init_lobby_groups(self, lobby_group_class, **kwargs):
        """Initialize lobby groups."""
        lobby_groups = []

        # Import AFT enum from farmer module
        from inseeds.components.farming.farmer import AFT

        print("Creating 2 lobby groups...")

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
        
        # Add lobby groups to the world's individuals list
        for lobby_group in lobby_groups:
            self.world.individuals.add(lobby_group)
            
        # Also store in world.lobby_groups for the update method
        if not hasattr(self.world, 'lobby_groups'):
            self.world.lobby_groups = set()
        self.world.lobby_groups.update(lobby_groups)
        
        print(f"Added {len(lobby_groups)} lobby groups to world. Total individuals: {len(self.world.individuals)}")
        
        return lobby_groups

    def update(self, t):
        super().update(t)

        # Reset subsidies and budget at the start of each year
        self.world.shared_subsidy_budget = 0.0
        for farmer in self.world.farmers:
            farmer.received_subsidy = 0.0

        # Calculate world total crop yield for shared budget calculation
        if self.world.farmers:
            world_total_crop_yield = sum(farmer.cropyield for farmer in self.world.farmers)
        else:
            world_total_crop_yield = 0.0
        
        # Calculate shared subsidy budget (40% of world total crop yield)
        budget_value = world_total_crop_yield * 0.4
        # Ensure it's a scalar value
        if hasattr(budget_value, 'item'):
            budget_value = budget_value.item()
        elif hasattr(budget_value, 'values'):
            budget_value = budget_value.values.item()
        
        self.world.shared_subsidy_budget = budget_value
        
        # Distribute subsidies to farmers proportionally to their crop land area
        self.distribute_subsidies_to_farmers()

        # Update farmers (after they receive subsidies)
        farmers_sorted = sorted(
            self.world.farmers, key=lambda farmer: farmer.avg_hdate
        )
        for farmer in farmers_sorted:
            farmer.update(t)

        # Update lobby groups
        lobby_groups_sorted = sorted(
            self.world.lobby_groups, 
            key=lambda lg: lg.lobby_group_id
        )
        for lobby_group in lobby_groups_sorted:
            lobby_group.update(t)

    def distribute_subsidies_to_farmers(self):
        """Distribute the shared subsidy budget to farmers proportionally to their crop land area."""
        if not self.world.farmers or self.world.shared_subsidy_budget <= 0:
            return
            
        # Calculate total crop land area across all farmers
        total_crop_area = 0.0
        for farmer in self.world.farmers:
            area = farmer.cell.area
            # Convert xarray to scalar if needed
            if hasattr(area, 'item'):
                area = area.item()
            elif hasattr(area, 'values'):
                area = area.values.item()
            total_crop_area += area
            
        if total_crop_area <= 0:
            return
            
        # Distribute subsidies proportionally
        for farmer in self.world.farmers:
            # Calculate farmer's share based on their crop land area
            area = farmer.cell.area
            # Convert xarray to scalar if needed
            if hasattr(area, 'item'):
                area = area.item()
            elif hasattr(area, 'values'):
                area = area.values.item()
                
            farmer_share = area / total_crop_area
            subsidy_amount = self.world.shared_subsidy_budget * farmer_share
            
            # Store the subsidy amount for output (optional)
            farmer.received_subsidy = subsidy_amount
        
 
        



