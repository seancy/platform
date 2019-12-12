function drawPieChart(elementId, data) {
  var containerEl = document.getElementById(elementId),
      width       = containerEl.clientWidth,
      height      = width,
      radius      = (width - 100) / 2,
      labelRadius = radius + 20,
      container   = d3.select(containerEl),
      svg         = container.select('svg')
                            .attr('width', width)
                            .attr('height', height);
  var pie = svg.append('g')
               .attr('transform', 'translate(' + width / 2 + ',' + height / 2 + ')');

  var pieData = d3.pie()
                  .sort(null)
                  .value(function(d) { return d.percent; })
                  .padAngle(0.02);

  var pieChartPieces = pie.datum(data)
                          .selectAll('.pieChart__arc')
                          .data(pieData)
                          .enter().append('g')
                              .attr('class', 'pieChart__arc');

  var pathArc = d3.arc()
              .outerRadius(radius)
              .innerRadius(radius * 0.6)
              .cornerRadius(2);

  pieChartPieces.append('path')
                .attr('d', pathArc)
                .attr('class', function(d) { return 'pieChart__' + d.data.color; })
                .on('mouseover', function(d) {
                  d3.select('#pieChart__label__' + d.data.color)
                    .attr('class', function(d) { return 'pieChart__label pieChart__' + d.data.color; });
                 })
                .on('mouseout', function(d) {
                  d3.select('#pieChart__label__' + d.data.color)
                    .attr('class', 'pieChart__label hidden');
                 });


  var labelArc = d3.arc()
                .outerRadius(labelRadius)
                .innerRadius(labelRadius);

  var f = d3.format("%");

  pieChartPieces.append('text')
                .attr("transform", function(d) {
                  var c = labelArc.centroid(d),
                      x = c[0],
                      y = c[1],
                      // pythagorean theorem for hypotenuse
                      h = Math.sqrt(x*x + y*y);
                  return "translate(" + (x/h * labelRadius) +  ',' + (y/h * labelRadius) +  ")";
                })
                .attr("text-anchor", function(d) {
                  // are we past the center?
                  return (d.endAngle + d.startAngle)/2 > Math.PI ? "end" : "start";
                })
                .attr('id', function(d) { return 'pieChart__label__' + d.data.color; })
                .attr('class', 'pieChart__label hidden')
                .text(function(d) {  return Math.round(d.data.percent*100) + "%";  });

}


function drawLineChart(elementId, csvData, redraw) {
  var containerEl = document.getElementById(elementId),
      width = containerEl.clientWidth,
      height = (containerEl.clientHeight < width / 2) ? containerEl.clientHeight : width / 2,
      container = d3.select(containerEl),
      svg = container.select('svg')
            .attr('viewBox', '0 0 '+ width  +' ' + height)
            .attr('width', '100%')
            .attr('height', '100%'),
      margin = {top: 10, right: 0, bottom: 23, left: 0},
      detailWidth  = 58,
      detailHeight = 35,
      detailMarginBottom = 10,

      areaWidth = width - margin.left - margin.right - detailWidth,
      areaHeight = height - margin.top - margin.bottom - detailHeight - detailMarginBottom,

      parseTime = d3.timeParse('%d-%m-%Y'),

      max_value = 0,
      data = d3.csvParse(csvData, function(d) {
        d.date = parseTime(d.date);
        d.value = +d.value;
        if (d.value > max_value) {
          max_value = d.value;
        }
        return d;
      });

  if (redraw === true) {
    svg.select('g').remove();
  }
  var lineChart = svg.append('g').attr('transform', "translate(" + margin.left + "," + margin.top + ")"),

      x = d3.scaleTime().rangeRound([0, areaWidth]),
      y = d3.scaleLinear().rangeRound([areaHeight, 0]),

      line = d3.line().x(function(d) { return x(d.date); })
                      .y(function(d) { return y(d.value); }),

      area = d3.area().x(function(d) { return x(d.date); })
                      .y0(y(0))
                      .y1(function(d) { return y(d.value); });

  x.domain(d3.extent(data, function(d) { return d.date; }));
  y.domain([0, max_value]);

  lineChart.append('g').attr('transform', "translate(" + (detailWidth / 2) + "," + (detailHeight + detailMarginBottom + areaHeight) + ")")
                       .call(d3.axisBottom(x))
                       .select('.domain').remove();

  var drawing = lineChart.append('g').attr('transform', "translate(" + (detailWidth / 2) + "," + (detailHeight + detailMarginBottom) + ")");

  drawing.append('path').datum(data)
                        .attr('class', 'lineChart--area')
                        .attr('d', area);

  drawing.append('path').datum(data)
                        .attr('class', 'lineChart--areaLine')
                        .attr('d', line);

  var circles = drawing.append('g')
  data.forEach(function(datum) {
      circles.datum(datum)
             .append('circle')
             .attr('class', 'lineChart--circle')
             .attr('r', 4)
             .attr('cx', function(d) { return x(d.date); })
             .attr('cy', function(d) { return y(d.value); })
             .on('mouseenter', function(d) {
                  d3.select(this).attr('r', 6);
                  var details = circles.append('g').attr('class', 'lineChart--bubble')
                                                   .attr('transform', function() {
                                                      var x_coord = x(d.date) - detailWidth/2;
                                                      var y_coord = y(d.value) - detailHeight - detailMarginBottom;
                                                      return "translate(" + x_coord + "," + y_coord + ")"
                                                   });
                  details.append('path').attr('d', 'M2.99990186,0 C1.34310181,0 0,1.34216977 0,2.99898218 L0,27.6680579 C0,29.32435 1.34136094,30.6670401 3.00074875,30.6670401 L24.4095996,30.6670401 C28.9775098,34.3898926 24.4672607,30.6057129 29,34.46875 C33.4190918,30.6962891 29.0050244,34.4362793 33.501875,30.6670401 L54.9943116,30.6670401 C56.6543075,30.6670401 58,29.3248703 58,27.6680579 L58,2.99898218 C58,1.34269006 56.651936,0 55.0000981,0 L2.99990186,0 Z M2.99990186,0')
                                        .attr('width', detailWidth)
                                        .attr('height', detailHeight);
                  details.append('text').attr('class', 'lineChart--bubble--value')
                                        .attr('x', detailWidth / 2)
                                        .attr('y', detailHeight / 2 + 2)
                                        .attr('text-anchor', 'middle')
                                        .text(d.value);
             })
             .on('mouseout', function(d) {
                  d3.select(this).attr('r', 4);
                  circles.selectAll('.lineChart--bubble').remove();
             })
             .transition()
             .delay(2000);
  });
}

function drawMap(elementId, csvData, mapJsonFile) {
  var containerEl = document.getElementById(elementId),
    width = containerEl.clientWidth,
    height = width * 0.6,
    container = d3.select(containerEl),
    svg = container.select('svg')
        .attr('viewBox', '0 0 '+ width +' ' + height)
        .attr('width', '100%')
        .attr('height', '100%');

  var values = d3.map();

  const scaleFactor = containerEl.clientWidth / 768, scaleDefault=170;
  scaleRatio = scaleFactor > 0 ? scaleFactor * scaleDefault : scaleDefault;
  var projection = d3.geoNaturalEarth1()
      .scale(scaleRatio)
      .translate([width / 2, height / 2*1.1])
      .precision(.1);
  var path = d3.geoPath(projection);

  var max_value = 0;
  var data = d3.csvParse(csvData, function(d) {
                values.set(d.id, [d.label, +d.value]);
                if (+d.value > max_value) {
                  max_value = d.value;
                }
             });

  var color = d3.scaleLinear()
      .domain([1, max_value])
      .range([0.1, 1]);

  //d3.json("https://d3js.org/world-110m.v1.json", function(error, world) {
  d3.json(mapJsonFile, function(error, world) {
    if (error) throw error;

    svg.append("g")
        .attr("class", "map--country-borders")
      .selectAll("path")
      .data(topojson.feature(world, world.objects.countries).features)
      .enter().append("path")
        .attr("d", path);

    svg.append("g")
      .selectAll("path")
      .data(topojson.feature(world, world.objects.countries).features)
      .enter().append("path")
        .attr("class", function(d) {
          if (values.get(d.id)) {
            return "map--country-color";
          }
          return "map--country-blank";
        })
        .attr("stroke", "none")
        .attr("opacity", function(d) {
          var value = values.get(d.id)
          if (value) {
            return color(value[1]);
          }
          return 1;
        })
        .attr("d", path)
      .append("title")
        .text(function(d) {
          var value = values.get(d.id)
          if (value) {
            return value[0] + "\n" + value[1];
          }
          return;
        });

    svg.append("path")
        .datum(topojson.mesh(world, world.objects.countries, function(a, b) { return a !== b; }))
        .attr("class", "map--country-borders")
        .attr("d", path);
  });
}
