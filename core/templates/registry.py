from enum import Enum

from core.log import get_logger

from .javascript_react import JavascriptReactProjectTemplate
from .node_express_mongoose import NodeExpressMongooseProjectTemplate

# from .react_express import ReactExpressProjectTemplate

log = get_logger(__name__)


class ProjectTemplateEnum(str, Enum):
    """Choices of available project templates."""

    JAVASCRIPT_REACT = JavascriptReactProjectTemplate.name
    NODE_EXPRESS_MONGOOSE = NodeExpressMongooseProjectTemplate.name
    # REACT_EXPRESS = ReactExpressProjectTemplate.name


PROJECT_TEMPLATES = {
    JavascriptReactProjectTemplate.name: JavascriptReactProjectTemplate,
    NodeExpressMongooseProjectTemplate.name: NodeExpressMongooseProjectTemplate,
    # ReactExpressProjectTemplate.name: ReactExpressProjectTemplate,
}
