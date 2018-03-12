angular.module('mocks', [])
    .controller('mocksController', function($http) {
        var context = this;
        var manageUrl = "../manage/";
        context.httpMethods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"];
        context.loadMocks = function() {
            $http({
                method: 'GET',
                url: manageUrl
            }).then(function successCallback(response) {
                context.mocks = response.data;
                resetCurrentMock();
            })
        }
        context.loadMock = function(id) {
            var url = manageUrl + id;
            context.currentId = id;
            $http({
                method: 'GET',
                url: url
            }).then(function successCallback(response) {
                context.currentMock = response.data;
                context.currentMock.json = JSON.stringify(context.currentMock.response, undefined, 4);
                context.currentMock.id = id;
            })
        }

        context.new = function() {
            resetCurrentMock();
        }
        context.update = function() {
            var id = context.currentMock.id;
            var url = manageUrl + id;
            if (context.currentMock.json) {
              context.currentMock.response = JSON.parse(context.currentMock.json);
            }
            else {
              context.currentMock.response = null;
            }

            delete context.currentMock.json;
            $http({
                method: 'PUT',
                url: url,
                data: context.currentMock
            }).then(function successCallback(response) {
                context.loadMocks();
                context.loadMock(id);
            })
        }

        context.create = function() {
            var url = manageUrl;
            if (context.currentMock.json) {
              context.currentMock.response = JSON.parse(context.currentMock.json);
            }
            else {
              context.currentMock.response = null;
            }
            delete context.currentMock.json;
            $http({
                method: 'POST',
                url: url,
                data: context.currentMock
            }).then(function successCallback(response) {
                context.loadMocks();
                var loc = response.headers("Location");
                var id = loc.split('/').pop();
                context.loadMock(id);
            })
        }

        context.duplicate = function() {
            context.currentMock.id = undefined;
        }

        context.delete = function() {
            var url = manageUrl + context.currentMock.id;
            $http({
                method: 'DELETE',
                url: url
            }).then(function successCallback(response) {
                context.loadMocks();
            })
        }

        var filterMocks = function(allMocks) {
            var mocks= [];
            for (mock in allMocks) {
              mocks.push(mock);
            }
            return mocks;
        }

        var resetCurrentMock = function() {
          context.currentMock = {
            "url":"/",
            "httpStatusCode":200,
            "httpMethod":"GET",
            "latency":{"min":null, "max":null},
            "headers":"Content-Type: application/json",
            "response":null};
        }


        context.loadMocks();

    });
