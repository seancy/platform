import 'select2'
import '../../../../node_modules/select2/dist/css/select2.css'

export class CourseReport {
    constructor(){
        $('.analytics-header form select').select2();
    }
}
