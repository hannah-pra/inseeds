import pycopancore.model_components.base as core
from pycopancore.data_model.variable import Variable
from pycopancore.data_model.master_data_model.dimensions_and_units import (
    DimensionsAndUnits as DAU,
)

from inseeds.components import base
from inseeds.components import farming
from inseeds.components.farming.management import tillage
from inseeds.components import lpjml
from inseeds.components.farming import LobbyGroup, DecisionMaker


class Farmer(tillage.Farmer):
    """Farmer entity type."""

    output_variables = base.Output(
        aft_id=Variable("AFT ID", "unique identifier for agent"),
        avg_hdate=Variable(
            "average harvest date",
            "weighted average harvest date of grown crops (by crop area)",
            unit=DAU.doy,
        ),
        soilc=Variable(
            "soil organic carbon",
            "soil organic carbon content of agent land",
            unit=DAU.gC_per_m2,
        ),
        cropyield=Variable(
            "average crop yield",
            "average crop yield of agent land weighted by crop area",
            unit=DAU.gC_per_m2,
        ),
        tillage=Variable(
            "agent tillage behaviour",
            "conventional=1, conservation=0",
            datatype=bool,
        ),
        pbc=Variable(
            "perceived behavioural control",
            "own appraisal of how much efficacy agent posesses",
        ),
        tpb=Variable(
            "theory of planned behaviour",
            "attitude, subjective norm, perceived behavioural control",
        ),
        social_norm=Variable(
            "social norm",
            "social norm based on observation of own and\
                                 neighboring land",
        ),
        attitude=Variable(
            "attitude",
            "farmer attitude based on observation of yield and soilC of\
                             own land and neighboring land",
        ),
        attitude_own_land=Variable(
            "attitude towards own land",
            "attitude based on observation of yield and soilC\
                                      of own land",
        ),
        attitude_social_learning=Variable(
            "attitude based on social learning",
            "attitude based on observation of yield and\
                                             soilC of neighboring land",
        ),
    )


class DecisionMaker(farming.DecisionMaker):
    """Decision Maker entity type."""

    output_variables = base.Output(
        decision_maker_id=Variable("Decision Maker ID", "unique identifier for decision maker"),
        belief_value=Variable("Belief Value", "decision maker's belief about the system (-1.0 to 1.0)"),
        world_average_cropyield=Variable("World Average Crop Yield", "average crop yield across all cells"),
        world_average_soilc=Variable("World Average Soil C", "average soil carbon across all cells"),
    )


class LobbyGroup(farming.LobbyGroup):
    """Lobby Group entity type."""

    output_variables = base.Output(
        lobby_group_id=Variable("Lobby Group ID", "unique identifier for lobby group"),
        aft_type=Variable("AFT Type", "agent functional type this lobby group represents"),
        belief_value=Variable("Belief Value", "lobby group's belief about the system (-1.0 to 1.0)"),
        
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
            "Agreement", 
            "fraction of majority practice among farmers"
        ),

        contributed_yield=Variable(
            "contributed crop yield",
            "total crop yield contributed by all farmers in this lobby group (10% each)",
        ),
        farmer_count=Variable("Farmer Count", "number of farmers in this lobby group"),
    )

    @property
    def farmer_count(self):
        """Get the number of farmers in this lobby group."""
        return len(self.farmers)


class Cell(lpjml.Cell, farming.Cell):
    """Cell entity type."""

    pass


class World(lpjml.World, farming.World):
    """World entity type."""

    pass


class Model(lpjml.Component, farming.Component):
    """Model class for the InSEEDS Social model integrating the LPJmL model and
    coupling component as well as the farmer management component.
    """

    name = "InSEEDS farmer management with lobby groups"
    description = "InSEEDS farmer management model representing social \
    dynamics and decision-making on the basis of the TPB with lobby groups"

    def __init__(self, **kwargs):
        """Initialize an instance of World."""
        # Initialize the parent classes first
        super().__init__(**kwargs)

        # Ensure self.lpjml is initialized before accessing it
        if not hasattr(self, "lpjml") or self.lpjml is None:
            raise ValueError("lpjml must be initialized in the parent class.")

        # initialize LPJmL world
        self.world = World(
            model=self,
            input=self.lpjml.read_input(),
            output=self.lpjml.read_historic_output().isel(time=[-1]),
            grid=self.lpjml.grid,
            country=self.lpjml.country,
            area=self.lpjml.terr_area,
        )

        # initialize cells
        self.init_cells(cell_class=Cell)

        # initialize farmers
        self.init_farmers(farmer_class=Farmer)

        # initialize decision makers
        self.init_decision_makers(decision_maker_class=DecisionMaker)

        # initialize lobby groups
        self.init_lobby_groups(lobby_group_class=LobbyGroup)

        self.write_output_table(
            init=True,
            file_format=self.config.coupled_config.output_settings.file_format,
        )

    def update(self, t):
        super().update(t)
        self.write_output_table(
            file_format=self.config.coupled_config.output_settings.file_format
        )
        self.update_lpjml(t)
